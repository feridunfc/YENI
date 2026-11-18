# YENI Engineering Recipe and Golden Integration Contract

## Purpose and delivery boundary

This document specifies how YENI takes a structural model from source acquisition through analysis qualification, member design, reinforcement selection, joint and storey evaluation, design iteration, and a reproducible engineering report. It preserves the previous 24-chapter recipe, 73 control identities, their worked examples, and the numerical method conditions. The main application is reinforced concrete building design under TBDY 2018 and TS 500. Other material and performance families remain explicit product profiles with their own methods and evidence requirements.

The integration package is a specification and verification asset. Its completion grants no engineering acceptance, closes no project GAP, and does not establish that a building or a production implementation satisfies a control. Existing calculation owners, `EnginePipelineRunner`, and the existing ETABS gateway remain the only production paths. Descriptive type names in this recipe are contract concepts unless `CHECK_MAPPING.json` identifies an inspected implementation. They are not claims that additional classes or functions already exist.

### Reviewed version and preservation

The integration branch is `baseline/local_import`. The published commit inspected for this delivery is **`b255c3030c09c88a17bbec766fc2bb22682ad027`**, with Git tree **`9cf5b99059cd107a1e447c398fd1e93b7292b31b`**. The file manifest records each retrieved file's Git blob identifier, raw SHA-256, size, and review role. A branch name alone is not a version record.

The user identifies **`a2e26b664d9b2b217e828de2c1df0c3df26068b1`** as the last verified local development commit and reports incomplete local changes above it. That commit and the dirty local tree are **`NOT_INSPECTED`**. The connected GitHub lookup did not find that commit; this does not establish that the local commit is absent. No ancestry or byte equivalence between the local tree and the published snapshot is asserted. Published mappings are evidence about the inspected snapshot only. Unverified owner connections are `UNMAPPED`.

The previous recipe referenced `8df69d2991338b3668f53a35c43f772a9bc4fa5e` and the D3B implementation base `85e720d18683a71737c1919d32e393c9d903737b`. Those references are historical provenance, not instructions to restore old code. This package supplies no reset, checkout, clean, rebase, merge, or source replacement operation. Local progress must be reconciled by content and evidence before using any published owner binding.

### Package contract

| File | Responsibility |
| --- | --- |
| `RECIPE.md` | Human-readable engineering procedure and integration conditions; source of the PDF and DOCX |
| `CHECK_MAPPING.json` | Exactly 73 existing control identities, applicability, inspected owners, input and output contracts, remaining work, and evidence |
| `GOLDEN_CASES.json` | Stable worked-example identities, source hashes and locators, inputs, intermediate steps, expected quantities, tolerances, and scenario coverage |
| `SOURCE_MANIFEST.json` | Inspected version, source and file identities, review boundary, public references, and private-source requirements |
| `VERIFICATION_RESULTS.json` | Separate current execution records and preserved historical evidence for all six verification levels |
| `schemas/` | Versioned JSON Schema contracts for the machine-readable delivery |
| `REVISION_NOTES.md` | Preserved content, transformations, corrected provenance, compatibility, and unresolved integration actions |

The publishable package contains derived technical records and source identities. Original private reports, databases, source access links, and the earlier unmodified delivery are kept in a separate private evidence package. An atlas page reference identifies a page in that private evidence package; it is not a missing page in the public report. Official public standards and manufacturer documentation may be linked in the public manifest.

### Separate populations and verification levels

The 73 recipe controls, 73 primary examples, 12 additional adapter fixtures, 94-node historical DAG catalogue, project-specific control instances, software tests, and assertion records are different populations. There is no combined compliance percentage. The existing production golden subset contains **44 historical records: 15 numerical matches, 25 insufficient-source records, and 4 engineering-interpretation differences**, as recorded by `EV-GOLDEN` for `85e720d18683a71737c1919d32e393c9d903737b`. It remains a separate protected evidence set and is not replaced by this bank.

The prior recipe arithmetic bank contains 333 assertion records. The separate PDF V2 bank contains 467 reference cases, of which its earlier verifier replayed a different subset of 333 comparisons. Their identical counts do not identify the same records. Historical results retain their original provenance and are not presented as fresh executions.

There is a preserved historical discrepancy in the 44-record evidence: the inspected `CURRENT_STATE.md` and `VERIFICATION_LEDGER.json` record 15 numerical matches, 25 insufficient-source records and 4 interpretation differences, whereas the older stored `docs/VS26_GOLDEN_REGRESSION.json` contains 13, 27 and 4 respectively. Both have 44 records, but their states are different. This delivery retains their separate hashes and provenance. It neither silently reconciles them nor labels either file as a newly executed comparison. The specific report supporting the later 15/25/4 event must be bound before record-by-record reconciliation can be accepted.

Verification is reported separately as: document/schema consistency; independent example arithmetic; comparison with an actual YENI calculation owner; recorded-source pipeline replay; live ETABS source validation; and engineering acceptance. A level not executed in this delivery is `NOT_RUN`. An inspected symbol or schema-valid file is not a production comparison. A synthetic fixture is not a live source validation.

### Safe local integration sequence

First preserve the local worktree and record its actual HEAD, branch, dirty tracked files, untracked code, interpreter, configuration, and relevant file hashes. Compare the inspected owner candidates with that local source. Confirm the function, signature, units, semantics, and dependency closure; a matching name alone is insufficient. Record a reviewed local binding or retain `UNMAPPED`.

Next validate schemas and cross-file identities. Run the independent example arithmetic. Bind supported cases to existing owners with explicit parameter and result-field mappings, then run those owner comparisons without replacing the 44-record regression. Replay a frozen recorded source through the existing runner and compare the full sealed inventory. Execute live source round trips only when the existing ETABS session and an explicit acquisition plan are available. Engineering acceptance requires a separate decision supported by the resulting evidence.

Formula strings are display-only. Production code must never execute a formula field using `eval`, `exec`, or a general expression interpreter. The package's narrow oracle functions reproduce fixed example arithmetic independently; they are not imported by production and do not implement a second section solver, design pipeline, or ETABS attachment path.

## 1 Define the design basis as one project profile

### 1.1 Initial project record

Record location, use, new or existing construction, structural materials, storeys, basements, the reference for building height, seismic joints, design life, exposure, and fire requirements. Keep owner preferences for material, bar diameters, construction, and cost in a separate design policy. A statutory minimum and a project preference must remain distinct fields.

Record ground-motion level, coordinates and map version, site class, any site-specific spectrum, building use class, importance factor I, earthquake design class, height class, performance objective, and analysis method. Establish the structural system and its R and D coefficients independently in each horizontal direction from the participating physical members and the applicable system conditions. Names and labels do not establish a structural-system classification. [N1, Chapters 2–4]

Freeze the standards package by code identifier, edition, amendment, clause, source SHA-256, interpretation decision, and applicable profile. The supplied TS 500 source is February 2000 with the T1/2001 and T2/2002 material present in that file; it is not labelled as an independently verified current consolidated edition. A new normative package creates a new method revision. An example report or spreadsheet is an illustration, not the normative authority.

### 1.2 Select the analysis route explicitly

Select the building family and performance target before choosing strength-based design (DGT) or deformation-based assessment/design (SGDT). Within DGT, test the applicability of equivalent lateral force, modal, and response-history routes against height, building classes, irregularities, and structural system. Within SGDT, select material laws, effective stiffness, plasticity idealisation, record selection, analysis procedure, and deformation limits together. Preserve the physical meaning of each route's outputs.

For the principal reinforced concrete DGT profile, declare ductility, frame/wall system, rigid or semi-rigid diaphragms, basement treatment, global and local second-order methods, effective beam flange policy, horizontal-direction combination, vertical-earthquake treatment, and foundation model. Each decision generates parameters and an applicable control population.

### 1.3 Establish applicability positively

Applicability depends on the project profile, geometry, topology, and action role. Its outcomes are applicable, a substantiated exemption, or referral to another method branch. The absence of an upper column at a roof joint, a short-column condition, and a beamless joint require physical evidence. An empty result table proves no exemption.

The project profile and physical inventory generate expected control instances. The 73 legacy headings, 94 DAG nodes, and thousands of member–combination–cut evaluations remain different counts. A new physical cut adds an instance, not automatically a new control identity.

## 2 Prepare the source package for the existing calculation path

### 2.1 Preserve four model responsibilities

| Model | Responsibility | Identity |
| --- | --- | --- |
| Physical | Built objects, storeys, joints, faces, spans, connectivity, and load paths | Model and physical Unique ID |
| Analysis | Mesh, analysis elements, joints, rigid zones, releases, cases, and result generation | Analysis generation and native element |
| Design | Sections, actual bars, ties/crossties, materials, and candidate or selected design | Design revision and candidate ID |
| Result | Source, method, demand, capacity, intermediate values, and decision | Run and control-instance identity |

A physical column can contain several analysis elements. Two element ends at an internal joint remain different force sides despite sharing coordinates. A cage revision can change while the physical Unique ID remains fixed. Maintain explicit joins between these models; storey labels or rounded coordinates are not primary keys.

### 2.2 Live acquisition transaction

The existing session owner binds model and process identity. Save the model file identity, present units, object selection, selected result cases/combinations, and any database-table display filters before temporary changes. Read in declared units and verify model/generation identity at critical boundaries. Restore temporary selections on success, error, and cancellation. Unit restoration follows the active, explicit capture policy: the inspected repository instructions authorize setting kN–m–C at attachment, so an authorized persistent unit change is not itself a restoration failure. Record the original units, selected policy and observed final units. The inherited restore-all-state recipe remains the default where no such authorization applies. Retain native return codes and the observed data contract.

Acquire physical objects and storeys; material/section assignments; local axes; frame/shell mesh; object and analysis-joint coordinates; connectivity; offsets, rigid zones and releases; output stations; load patterns, cases and combinations; mass and modal settings; generation and convergence logs; displacements, participation, storey forces and reactions; frame/shell/pier results; and reinforcement templates and design settings. Each family has a native schema/version record.

Acquisition and permanent model mutation are distinct operations. Capture does not silently analyse the model or write reinforcement. If a change affects analysis, prepare a concrete request identifying the changed geometry, stiffness, mass, loads, and expected new generation.

### 2.3 Offline acquisition

Adapt recorded ETABS packages, JSON shards, SQLite/HDF5 banks, or verification fixtures to the same source contract and existing runner. Verify manifests and hashes, retain native fields, and read the physical roster independently. `producer`, `acquisition_mode`, `intended_use`, and `response_semantics` are separate attributes: an ETABS archive and a synthetic fixture do not gain the same authority by sharing a schema.

Record filename, size, SHA-256, schema, model/generation, acquisition time, and parent package. Validate normalised paths, duplicate ZIP entries, and expanded-size limits. Keep raw evidence immutable; a policy or cage experiment creates a separate scenario identity. No second offline formula engine is introduced.

## 3 Establish engineering geometry and calculation cuts

### 3.1 Units and signs

Use N–mm–MPa in the section kernel and explicitly named kN–m–kNm fields at analysis boundaries. Convert once at the adapter; never infer units from magnitude. Preserve native CSI P, V2, V3, T, M2, and M3 with their source axes and signs. A compression-positive domain may use N = −P only when that adapter convention has been verified with directional examples. [N4]

Local 1 is the member axis. M2 acts about local 2 and produces strain variation along local 3. For physical dimensions t2 and t3, the bending depth is t3 for M2 and t2 for M3. Distinguish native and already-local dimension types to prevent duplicate conversion. AxisAngle supports global projection; it is not a reason to rotate an already-local section again.

For reference transfer, use F_target = R F_source and M_target = R M_source + r × F_target, where r runs from target origin to source origin and is expressed in target axes. Convert compression-positive section N back to the correct physical force component before vector operations. Include loads acting between cuts in the force and moment balance. Rotating only M2/M3 does not complete an eccentric face transfer.

### 3.2 Storeys and lengths

Treat Story as an identity. Interpret a numeric-looking label as an elevation only when the source schema explicitly establishes that meaning. Otherwise use validated base elevation, physical heights, and bottom-up ordering; reconcile derived elevations with joint coordinates. Alphabetical or incidental table order is insufficient.

Keep axis length, end offsets, rigid-zone length, physical joint faces, clear span, and effective buckling length separate. Clear span ln is measured between physical faces; lk = k·l belongs to the selected buckling model. Mesh length replaces neither automatically. Infill restraints, short-column conditions, intermediate supports, and connection flexibility must appear in the physical basis.

### 3.3 Maintain three cut inventories

Maintain the configured output-station inventory, the native analysis-element cut inventory, and the engineering-required cut inventory. Required cuts include physical end faces, both sides of internal connections, load/geometric discontinuities, section and reinforcement changes, support shear regions, span moment extrema, and confinement boundaries. Three configured output stations do not establish a complete physical census. [N5]

A cut key includes source/model/generation, physical member, analysis element, element side, object station, element station, and reference face. A matching tolerance supports joining; it does not replace identity. A coordinate window must yield a unique permitted match. Distinct element sides remain distinct. Multiple design-rebar rows at exactly one station may support an area envelope after section and message validation; different stations cannot be merged into that same-station envelope.

Reuse the existing PMM v6 directed multi-element column treatment: orient the connected chain I-to-J, bind independently acquired joint coordinates, and count both sides at each internal joint. The historically verified configured branch uses Min Stations = 3, zero I offset, and an oriented vertical chain. General offsets, intermediate loads, other orientations, and other families need explicit branches and independent inventories. Record every required case/combination and step before reading successful force rows.

## 4 Compile loads and design demands

### 4.1 Action and combination books

Patterns, analysis cases, and design combinations are different objects. Cases sharing a pattern may use different initial stiffness, P–Delta states, nonlinear history, or scales. Preserve each case's analysis type, initial state, constituent loading, step semantics, and generation.

Classify permanent, imposed, snow, wind, temperature, earth/water pressure, settlement, construction, and seismic actions in the project basis. Store combination operators and children as a graph. ULS, SLS, seismic design, capacity design, geotechnical, P–Delta initial-state, and performance roles are explicit. A substring such as Seis or Duct is not a role assignment.

Generate the required combinations from the frozen normative profile, including signs, directions, vertical effects, favourable/unfavourable gravity, patterned loading, and simultaneity rules. The selected combination list must be independent of the returned force rows. Establish the expected member × combination × cut × step population first.

### 4.2 Preserve demand semantics

| Demand type | Meaning | Permitted use |
| --- | --- | --- |
| Signed static state | Six signed components at one case and cut | Equilibrium and qualified linear superposition |
| Signed time state | One record, time step, and cut | Step-specific capacity and performance |
| Scalar component envelope | Separate lower/upper bounds per component | Component bounds and a qualified conservative procedure |
| Code design demand | Effect produced by one declared code method | Consumers allowed by that method |
| Capacity design demand | Effect derived from selected reinforcement capacities | Capacity shear, joints, ties, and related detailing |

Linear Add does not make envelope inputs concurrent. Carry leaf-case semantics through Linear Add, SRSS, Absolute Add, Envelope, and Range Add. Ordinary six-component vector addition is valid only on its qualified signed linear branch. [N3, N6]

### 4.3 Recover a seismic component from mixed demands

Reuse the existing exact-rational mixed-demand owner. At one cut and compatible step, write observed combinations as y = A·x. A desired effect e = cᵀx is identifiable when cᵀ lies in A's row space: solve Aᵀw = c and obtain e = wᵀy. Record rank, coefficients, native cases, and replay residual. Full recovery of every primitive x is not required to identify a particular functional.

For C = 1.2G + E with compatible G, E = C − 1.2G. A similarly named case from a different source, generation, initial state, or cut side is not that G input. Nonlinear histories are outside this linear-superposition route.

### 4.4 Record each demand transformation

For every transformation record its effect kind, input/output identities, factor or operation, axis, reference point, clause, application level, and revision. Apply unit/geometry conversion, qualified modal/directional procedures and source scales, then the consumer-specific second-order, minimum-eccentricity, capacity, and alpha operations in the declared method order. Global P–Delta, local P–delta, spectrum scaling, overstrength D, and 1/alpha are distinct effects. Do not repeat an effect already present in the source. Rebuild every iteration from immutable base demand and current absolute factors.

### 4.5 Plan from design combination groups

Keep four selections separate: physical member groups; YENI engineering combination groups; native ETABS design-combination selection; and temporary output filters. GroupElm is a physical group; a YENI ULS or seismic role is not SelectedForOutput. Defining a combination does not assign it to every native design procedure. [N8, N9]

The selection record binds actual combination IDs, role, member family, model, generation, and catalogue hash. A native concrete-design selection may initialise the user's selection but does not replace the explicit YENI role book. The inspected pipeline includes ASSIGNED_DESIGN and ETABS_STRENGTH paths; exact inspected owner evidence is in the mapping.

| Required role | Consumer | Required evidence |
| --- | --- | --- |
| Strength design | Axial, PMM, flexure, shear | Selected complete design combinations |
| Ductile seismic design | TBDY axial and seismic member checks | Explicit seismic role and direction |
| Service | Deflection and cracking | SLS family and service assumptions |
| Capacity design | SCWB, Ve, joint panel | Bound cages and directional capacities |
| Storey seismic effect | Alpha and global second order | Common directional scope, shears, drifts, and weights |
| Initial P–Delta state | Analysis stiffness qualification | Initial loads, case chain, and convergence |
| Sustained load and TS 500 storey state | Rm, sway classification, beta_s | Relevant load ratios and complete compression-member scope |

Keep user-selected `design_combinations` separate from supporting `required_source_cases`. A single-column SCWB request expands source dependencies to the attached columns and beams. Alpha or beta_s may require a complete storey. Capturing neighbouring evidence does not authorise changing neighbouring designs; their recorded cages may remain fixed constraints.

### 4.6 Reconcile missing or incomplete TBDY combinations

Read names, operators, case/combination child types, coefficients, analysis methods, and source identities. Bind actual G, Q, S, H, and seismic sources from the action book; retain wall and superimposed permanent loads within the correct gravity lineage.

On the applicable concrete DGT branch, TBDY 4.4.2 and 4.4.4 use EdH = ±EdX ± 0.3EdY and EdH = ±0.3EdX ± EdY, with G + Q + 0.2S + EdH + 0.3EdZ and 0.9G + H + EdH − 0.3EdZ. S denotes snow and H horizontal earth pressure. Under the approximate vertical branch, EdZ = (2/3)SDS·G, giving gravity coefficients 1 + 0.2SDS and 0.9 − 0.2SDS. This substitution belongs to 4.4.3.2; members requiring the special vertical analysis of 4.4.3.1 need that separate source. A concurrent response-history route does not receive an additional 100/30 rule by default. [N1, 4.4.2–4.4.4]

Reconcile existing R/I, D, eccentricity, direction combination, spectrum scaling, and vertical effects before compilation. Do not apply 100/30 twice to an already-combined case. Apply D only where its method branch requires it. Nonseismic strength, service, and foundation families have their own rules; there is no universal fixed number of TBDY combinations.

Preserve the source combination graph. Flattening is allowed only for compatible signed linear semantics and initial states. Envelope, SRSS, and nonlinear operators must not be converted to an ordinary coefficient vector merely because an example gives the same scalar answer.

Assign one reconciliation action to each expected combination:

1. Reuse an identical definition without duplication.
2. Add only a missing role or design assignment when the definition is correct.
3. Create a versioned user-defined combination when the definition is missing and its leaf cases exist.
4. For a name collision with different content, expose the difference and default to a new versioned name; change a user's definition only through the selected mutation plan.
5. When a leaf load or analysis case is absent, prepare the required load, spectrum, stiffness, and analysis operations with explicit project inputs. Do not fabricate loads, site parameters, or analysis results.

Create dependencies before their consumers and reject cycles. Keep engine-managed combinations distinct from automatically regenerated native design combinations. [N10]

### 4.7 Acquire internal forces from the plan

Freeze member, required case/combination, analysis element/side, cut, and step keys before acquisition. Bind a dynamic step inventory to recorded analysis/output settings. Show the dependency expansion for a joint or storey calculation in both counts and identities.

Within the existing session, save output selections and units, apply temporary result filters, read, and restore temporary filters in all exit paths. Apply and verify the explicit unit policy described in Section 2. API result selection and DatabaseTables display selection are separate adapter concerns; changing one does not prove the other changed. [N9]

Retain Obj, ObjSta, Elm, ElmSta, LoadCase, StepType, StepNum, P, V2, V3, T, M2, and M3 together. Add source/generation, units, and axis lineage. A signed vector's components come from one row identity. Envelope rows retain their separate-bound meaning. Storey shears, displacements, weights, and reactions have their own compatible keys. [N4]

Evaluate native return codes together with array lengths, declared row counts, finite values, case identity, and the independent expected cut inventory. Missing data are not zero forces. Perform unit/sign/face conversion only after source identity and coverage have been reconciled.

### 4.8 Verify getter and setter round trips

The transaction is GET → NORMALISE → DIFF → PLAN → APPLY → GET → VERIFY → SAVE. The getter returns observed native state, not the requested value or a successful setter's cache. Verify model identity, catalogue signature, lock state, and installed API capabilities before applying a plan; rebuild the plan if its preconditions changed.

The documented combination interface includes GetNameList, GetTypeCombo, GetCaseList, Add, SetCaseList, and DeleteCase. SetCaseList adds or modifies one child; writing all desired children does not remove old extra children. Compare the complete child multiset and operator before and after mutation. If an operator change is unsupported, plan a versioned replacement and its dependencies instead of assuming blind recreation is safe. These are manufacturer API references; actual installed-version tuples, enums, signatures, and return positions need adapter qualification. [N11, N12]

Compare coefficients under a stated normalisation tolerance and compare identifiers, child types, operators, signs, membership, and multiplicity structurally. Merge duplicate terms only when the operator permits that simplification. Do not assume that a method documented on another design class exists on concrete design. Use the installed version's verified OAPI or editable-table path for native design assignment and read it back from the same native source.

Handle lock restrictions from a capability record; do not unlock automatically after every error. Geometry, stiffness, mass, initial P–Delta state, or a new analysis case normally requires renewed analysis lineage. A combination derived from existing compatible results requires a separately checked result-validity decision. Its design report still receives a new revision. [N13]

COM calls are not inherently atomic. Journal original definitions, assignments, applied actions, and readback observations. On partial failure, restore only changes owned by the plan or recover a controlled working copy. Verify rollback by getter. Restoring definitions does not itself restore analysis results invalidated by unlocking or model changes. Reconcile generation and analysis validity afterwards. Repeating an unchanged plan must produce no mutation, duplicated combination, or compounded factor.

### 4.9 Use the same plan offline

Build the same role and combination plans offline. Derive qualified linear combinations from sufficient primitive signed results of the same generation and record producer ENGINE_DERIVED plus parent rows. Preserve envelope and nonlinear semantics. A request requiring a new case, stiffness, or P–Delta state becomes a concrete preparation/analysis plan for the existing live path; old archive rows are not results of that new model.

## 5 Complete building analysis and global checks

### 5.1 Spectrum and mass

Build the horizontal spectrum from SDS = SS·FS, SD1 = S1·F1, TA = 0.2SD1/SDS, and TB = SD1/SDS, using every applicable period branch and continuity checks at 0, TA, TB, and TL. Distinguish dimensionless acceleration in g from the acceleration units used by a case scale factor. Report the combined physical acceleration of the function and case scaling. [N1, Chapter 2; N6]

Maintain a mass ledger for permanent loads, live-load participation, self-weight, and assigned masses. Calculate storey mass, centres, and rotational inertia. Detect double counting between pattern self-weight and separately assigned loads. Reconcile totals with loads and reactions. Seismic mass, the TBDY weight ledger, and initial P–Delta loading remain separate objects.

### 5.2 Modal solution

Freeze effective stiffness, mass source, constraints, modal type, mode inventory, and solver tolerances. Record periods, shapes, X/Y effective masses and participation. Check total and individually significant-mode requirements in each direction. Bind active per-mode damping and the selected correlation rule, including closely spaced modes. A scalar case damping value alone does not prove every active mode's damping.

### 5.3 Base shear and directions

Compute the equivalent-lateral-force reference with the applicable period cap and minimum-force conditions, then compare modal base shear at the same direction and building scope. Apply required scaling exactly once. Keep force and displacement scaling branches distinct. Record applied accidental eccentricity, horizontal-direction combination, and vertical-earthquake effects explicitly.

For drift, TBDY 4.9.1.1 excludes the 4.7.3.2 period condition and the minimum equivalent load condition in Equation 4.19 from the displacement calculation. Therefore the force scaling factor cannot be copied to all drift records without its method-specific basis. GE-CHK-104 and GE-CHK-105 preserve that distinction. [N1, 4.9.1.1]

For basement/superstructure treatment, bind the selected common or separate analysis route, interface force transfer, rigid-basement assumptions, and scales. Do not add results generated for inconsistent scopes.

### 5.4 Irregularities and drift

Evaluate A1 from compatible diaphragm/point drift extremes and means; A2 from floor discontinuity; A3 from plan projections; B1 from adjacent-storey strength/effective-area relationships; B2 from stiffness relationships; and B3 from vertical load-path discontinuity. Preserve both the numerical criterion and its consequence for the analysis route. Applicability and exceptions remain clause-specific. [N1, Chapters 3–4]

Keep reduced versus effective drift, interstorey displacement difference, lambda, kappa, R, I, storey height, direction, and governing physical point explicit. Choose the infill/facade connection branch. Do not add R/I again to a source value whose definition already includes it.

### 5.5 Global second order and equilibrium

Compute storey stability from compatible drift, cumulative vertical weights, storey shear, and height. Follow the selected amplification or second-order route with consistent force/displacement scales. For native initial P–Delta, record which linear/modal cases inherit the stiffness and whether the analysis converged. [N1, 4.9; N7]

Produce separate load–support reaction, storey shear–member contribution, and superstructure–foundation balances. Signed static/time states support algebraic equilibrium. Spectral totals require their modal aggregation method; sums of independently combined maxima are not simultaneous equilibrium.

### 5.6 Bind P–Delta case by case

Expand each selected combination into leaf cases and bind stiffness source, initial case and loads, geometric-nonlinearity option, effective stiffness, generation, and convergence. Distinguish NONE, mass-based preset, iterative load-based preset, and nonlinear initial-state routes. NonlinCase = None does not exclude a preset initial P–Delta state, and a locked model does not prove second-order analysis. Preset initial P–Delta and a nonlinear-static case have different ownership; CSI documents the latter as a separate treatment. [N7, N14]

For the applicable TBDY route, theta_II,i = Delta_i,avg·sum(w_k)/(Vi·hi), using average reduced relative drift and the relevant storey plus upper-storey weights. The threshold is 0.12D/(ChR). Below it, the additional factor is one; otherwise beta_II = max(1, 0.88 + (ChR/D)theta_max). Ch = 0.5 for reinforced concrete. Apply the selected directional factor over its prescribed scope, including the upper-building scope where the rigid-basement branch requires it. [N1, 4.9.2]

Keep TBDY beta_II, TS 500 storey/sway beta_s, and TS 500 member beta as three effect identities. Beta_s is not exclusively local P–delta. Record separately the physical effects already solved by the source, the normative obligation, and the extra engine transformation. The joint method profile defines which effects are covered; neither blind multiplication nor skipping all factors because one P–Delta flag exists is valid. Changing initial loads or stiffness requires a new analysis generation; historical forces remain archived evidence only.

## 6 Use the existing section capacity kernel

### 6.1 Materials and reinforcement

Version concrete strengths, modulus, Poisson ratio, density, ultimate strains, compression-block or nonlinear law, and steel strengths, modulus, strain limits, and hardening. Keep TS 500 DGT idealisations separate from confined-concrete or cyclic SGDT models. Establish the permitted material range first. [N1, N2]

Compute As from actual bars, with diameter, local coordinates, material, layer, and role. Declare whether steel displaces concrete as point bars or exact disks and how net concrete area is defined. Use the same physical idealisation throughout a comparison. A fixed set of oracle functions in this delivery does not replace this production kernel.

### 6.2 Strain compatibility and resultants

Declare a plane-section sign convention, such as strain(x2,x3) = strain0 + curvature2·x3 − curvature3·x2. Integrate concrete and bar stresses into N, M2, and M3 about the same reference. Retain separate contributions and equilibrium residuals.

Separate requests for resultants at a given strain state, a capacity boundary at fixed N, and radial moment capacity in a specified direction at that N. Candidate selection belongs outside the section kernel: the same owner evaluates each permitted cage.

### 6.3 Numerical quality

Bracket neutral-axis roots for N(c,theta) − Nd = 0, include pure compression/tension and strain-limit states, and handle multiple admissible roots explicitly. Record integration accuracy, angular resolution, root residual, and convergence.

A radial utilisation requires a capacity slice that contains the moment origin and has the relevant admissible outer intersection. For asymmetric cages or composite sections, evaluate actual set membership or ray entry/exit intervals when that condition fails. A convex hull can enlarge resistance and is not automatically conservative. Detect self-intersection and invalid topology; avoid division by a vanishing moment component.

Use separate dimensional tolerances for positions, forces, moments, angles, and utilisation. Declare absolute/relative scale rules. Display rounding must not determine acceptance at a code boundary, and numerical tolerance must not silently relax a normative limit.

## 7 Design columns through all dependent checks

### 7.1 Geometry and axial limits

Establish section geometry, material/ductility scope, gross area Ac, topology, and physical lengths. Do not subtract steel area from Ac for the gross-area axial limits; real geometric voids remain part of the section definition. Evaluate TS 500 Equation 7.7, Nd ≤ 0.90fcdAc, and TBDY 7.3.1.2, Ndm ≤ 0.40fckAc, on their own required action populations. A large raw section resistance does not remove either limit. [N1, N2]

Retain governing combination, cut, sign, and role. General TS 500 design demands and the specified TBDY seismic Ndm population cannot be collapsed into one unqualified maximum.

### 7.2 Minimum eccentricity

Under TS 500 6.3.10, e_min = 15 + 0.03h in mm; h is the strain-variation depth. Thus h = t3 for M2 and h = t2 for M3. With compression N, M_min = N·e_min and each design magnitude is at least max(abs(M), M_min). Preserve an existing sign. At zero moment, consider the sign branches needed by an asymmetric cage. Do not satisfy one axis by deleting the other. [N2, 6.3.10]

### 7.3 Slenderness and local second order

Determine inertia, radius of gyration, end-moment ratio, restraints, and sway class for each local axis. Derive k from the qualified system/restraint model rather than the member label. If the omission criteria apply, retain their lengths and moments as evidence; otherwise use the selected second-order method.

Use the declared concrete/rebar stiffness and sustained-load/creep ratio Rm to compute Nk = pi²(EI)_eff/lk² per axis. Evaluate the applicable Cm, Nd/Nk, minimum factor, and domain conditions. A zero or negative denominator is not clipped to an arbitrary finite factor. A changed cage changes Is, EI, Nk, and magnified demand. Global source P–Delta does not automatically cover local member effects, and a source that already covers an effect must not receive it twice. [N2, 7.6]

### 7.4 Generate longitudinal candidates

Generate a finite cage family from permitted diameters, ratios, cover, tie diameter, layers, and face-bar counts. Place actual corner and intermediate bars without double counting corners. Check clear spacing, aggregate/construction conditions, layers, and detailing. The minimum area is the greater of the applicable code floor and stricter project floor; equality is accepted. Check maximum ratio and lap regions separately.

Keep TEMPLATE, PROPOSED, ALGORITHM_SELECTED, ENGINEER_APPROVED, and AS_BUILT meanings distinct. A native design template is not an approved physical cage. Evaluate every required demand/cut together with axial, second-order, PMM, placement, and detailing conditions. Use an explicit deterministic objective: satisfy mandatory constraints, then minimise area, then apply stated diameter/constructability tie-breaks. Claim minimum steel only within the searched candidate family.

### 7.5 End capacities and transverse reinforcement

For the same cage revision, calculate lower/upper face capacities for required directions, signs, and axial-force bases. Keep nominal, design, and probable capacities separate. The end-capacity record binds member, face, N source, mechanism, cage, and method revision for reuse by SCWB, panel shear, and capacity shear.

Construct column Ve from the two-end mechanism and clear span, with each end moment's applicable branch identified. When both ends are physically beamless, apply the required end-capacity treatment to both; one 1.4Mr term is not the entire column shear. In the own-column-capacity branch, use the direction-compatible axial demand that maximises the required moment resistance, distinct from SCWB's minimum-resistance selection. Apply the analysis-shear floor and prescribed upper/alternative bounds. [N1, 7.3.7]

Locate confinement, central, and joint regions physically. Check tie diameter, spacing, actual effective legs, crosstie support, hooks, first tie, confinement area, and shear resistance in both directions. In-plane unsupported longitudinal-bar spacing a and longitudinal tie spacing s are different quantities. Several legs alone do not prove every bar is laterally supported.

### 7.6 Bind reinforcement before capacity-dependent consumers

Bind a concrete cage to its physical member and region in the DesignModel; native ETABS writeback is a separate export operation. Check mode holds the supplied cage fixed. Design mode evaluates a proposed revision before selecting it. Required steel area or an ETABS template cannot substitute for coordinates and topology.

| Consumer | Required reinforcement information |
| --- | --- |
| Gross-area axial and global analysis checks | Cage-independent inputs, with the analysis stiffness basis separately fixed |
| PMM and directional Mr | Actual longitudinal bar coordinates and material |
| Reinforcement-dependent EI and magnification | Is from that same cage in each axis |
| SCWB | Bound lower/upper column and relevant beam-end longitudinal cages |
| Capacity shear | Valid end capacities from those cages |
| Joint panel | Effective beam bars and column shear from the same mechanism |
| Shear strength, confinement, and crossties | Compatible longitudinal and transverse cages with actual leg topology |

The design sequence is longitudinal candidate → EI/Nk/magnification and PMM → end capacities/SCWB/Ve → transverse selection and verification → re-evaluation of all affected constraints. If tie selection changes cover or longitudinal-bar coordinates, recompute capacity. SCWB need not wait for unrelated final tie details, while final member acceptance requires the complete detailing scope.

For the reinforcement-dependent TS 500 branch, EI = (0.2EcIc + EsIs)/(1 + Rm), Nk = pi²EI/lk², and beta = max(1, Cm/(1 − 1.3Nd/Nk)), subject to the method's positive-denominator and other conditions. Where beta_s applies, use compatible sum(Nd) and sum(Nk) for the complete compression-member scope: beta_s = max(1, 1/(1 − 1.3sum(Nd)/sum(Nk))). Do not sum individual Nd/Nk ratios. TS 500 small/large end moments are not the CSI local-2/local-3 axis names. [N2, 7.6; formula appendix]

Before native rebar writeback, inspect shared section assignments. A one-member change must not alter every user of a shared property unintentionally. Where appropriate, create a distinct property and assign only selected targets. Read back rebar, steel, cover, axes, design/check setting, and section assignment. Route analysis-stiffness changes to a new analysis plan; route design-only changes to all affected design consumers.

## 8 Complete beam design

Start from section geometry, effective flange, clear span, support faces, releases, continuity, torsion, and the complete design-demand population. Evaluate the applicable width/depth and column-connection conditions. The compression contribution of a slab flange and the anchored slab reinforcement effective in SCWB/joint tension are distinct inputs and methods.

Check support top/bottom and all required span sections. An envelope of trusted AsTop, AsBot, and total-area rows at one identical design station retains its contributing source rows. Convert required area into actual bars; an automatic area result is not a selected cage. Check continuity, top/bottom ratios, minimum reinforcement along the span, extension into supports, cut-off, and anchorage together.

Calculate positive and negative end capacities from the selected cage. Probable capacity used for capacity design carries its own strength assumptions. Combine mechanism shear and unfactored vertical-load simple-beam shear with signed equilibrium: Ve = Vdy ± (Mpi + Mpj)/ln. Vdy has the meaning of the applicable TBDY symbol definition and must remain separate from factored analysis design shear Vd. Evaluate both ends and earthquake signs. A single maximum absolute analysis moment cannot populate both ends. [N1, 7.0 and 7.4]

Evaluate the analysis demand, capacity demand, concrete-contribution branch, stirrup contribution, and concrete crushing limit together. Count actual effective stirrup legs. Where torsion applies, design shear–torsion interaction, closed ties, and additional longitudinal bars at the same section. Redistribution of compatibility torsion requires its selected analysis/code basis; equilibrium torsion cannot be discarded by that label. [N1, 7.4.5; N2, Chapter 8]

Resolve confinement length, first stirrup, spacing, hooks, laps, anchorage, and joint-core fit with physical bar geometry. Use appropriate service combinations for immediate/long-term deflection, cracking, and applicable vibration checks. The result contains bars, regional stirrups, governing cuts, intermediate values, and criteria, rather than only an As-required table.

## 9 Evaluate joints and strong column weak beam behaviour

### 9.1 Physical joint assembly

Assemble lower/upper columns, beams in each direction, physical faces, offsets, beam penetration, effective width, and confinement classification into one joint identity. Produce one joint result for member reports to reference. Beamless, one-sided, exterior, corner, and interior branches follow physical topology. Beam absence in one direction does not imply absence in the other; confinement requires the specified beam-width, face, and connection conditions. [N1, 7.5]

### 9.2 SCWB

For each required earthquake direction and rotation mechanism, sum bound column and beam end capacities. The standard TBDY 7.3.5 condition is sum(Mrc) ≥ 1.2sum(Mrb), with its own exemptions and axial-demand selection. For SCWB, select the direction-compatible Nd giving the smallest relevant column moment capacity. The own-capacity shear branch may instead require the largest capacity. These two consumers must not share an unqualified governing-N selector.

Include slab bars in beam capacity only where they are physically anchored and effective under the selected rule. Show every column and beam term, face, direction, sign, axial scenario, capacity type, and cage revision. A result in one mechanism does not stand in for another.

### 9.3 Joint panel shear

Derive panel shear from beam-bar yield/probable forces and column shear in one compatible mechanism. If the 1.25fykAs branch applies, identify the contributing bars and faces. Preserve column-shear sign and moment-transfer direction. Compute the correct effective joint area and resistance for confined or unconfined classification. Check core transverse reinforcement continuity, bar passage, and anchorage separately. [N1, 7.5.2]

After an alpha revision, rebuild the joint equilibrium with compatible current terms. Subtracting newly amplified column shear from stale beam forces can create an artificial improvement or deterioration. A valid change is explained by the complete updated mechanism.

### 9.4 Reinforcement prerequisites

Bind each participating end's longitudinal cage, material, face, direction, capacity method, and iteration revision before SCWB. Distinguish a physically absent member from an unacquired neighbour; the latter is not a zero-capacity member. A bound proposed cage can participate in an iteration, while a final selected/approved design requires the corresponding complete downstream evidence.

Increasing beam reinforcement can increase Mrb and invalidate an earlier SCWB result. Column or beam cage changes invalidate end capacity, SCWB, Ve, panel, and relevant storey results. Keep the complete alpha population separate from the TS 500 beta_s population. The existing candidate-binding and iteration owners remain responsible; the mapping states which exact inspected symbols implement the supported quantities.

## 10 Couple storey alpha with design iteration

### 10.1 Storey ratio and amplification targets

For TBDY 7.3.6, form the full relevant frame-column inventory at one storey, earthquake direction, and common physical cut. Use bound joint/cage results to identify the columns contributing to Vis and compute alpha_i = Vis/Vik against the same-scope total. Apply the relevant 0.70 ≤ alpha_i ≤ 1.00 condition and 1/alpha_i treatment. [N1, 7.3.6]

Do not sum maxima from different combinations. On a signed static route, use one compatible seismic component. On a modal route, establish the approved system-level aggregation or design-demand policy. Absolute-value conversion of opposite-signed member contributions is not a neutral operation. Frame-column shear and total building or wall-inclusive shear are different denominators.

Keep `vis_members` and `amplify_members` separate. A low-axial-load exemption may affect numerator inclusion without proving that both ends actually meet the strong-column condition required for amplification targeting. Columns failing the condition retain their applicable gravity and seismic design requirements.

The inherited `ALPHA_TOTAL_MV_V1` policy applies an absolute 1/alpha to M2, M3, V2, and V3 of the designated seismic design scenarios; N and T are unchanged by this effect. Record the seismic-only shear used to calculate alpha separately from the final combination being amplified. X and Y factors must not be multiplied successively into one combination. Build separate required directional scenarios from the immutable base and evaluate their complete union.

The code text in TBDY 7.3.6.2 refers to increasing moments and shears; an E-only implementation is a separate declared interpretation, such as `ALPHA_E_COMPONENT_V1`, and requires its own acceptance. Reusing the existing total-M/V implementation does not itself approve the method. If alpha is below 0.70, reassess the applicable system/ductility and R/D branch and produce the required revised analysis/design scenario.

### 10.2 Iteration state and invalidation

An iteration binds source, policy, evaluated demands, selected candidates, end capacities, joint results, storey factors, and detailing. The source remains immutable and every derived record identifies its parents. A cage change may affect EI/Nk, magnification, PMM, end capacity, SCWB, Ve, confinement, and related joint/storey consumers. Recompute the affected closure; do not repeat unrelated independent calculations without changed inputs.

First evaluate candidates against qualified base demands, then joints and storeys, then feed current alpha and capacity-shear requirements back to the member evaluator. Preserve mandatory constraints discovered earlier; a low final PMM ratio does not erase shear or second-order requirements.

### 10.3 Algorithm and termination

The following is explanatory orchestration, not a second executable pipeline. The actual implementation must extend the existing runner and its owner calls.

```text
Freeze project profile, code edition, and design policy.
Validate source, physical inventory, and required cuts.
Compile immutable base demands and initial candidate state.
For each permitted iteration:
    Evaluate candidates with the current demand and carried constraints.
    Calculate directional end capacities from those candidates.
    Evaluate joint mechanisms and complete storey rules.
    Derive absolute target factors and rebuild proposed demand from the base.
    Evaluate detailing against the demand actually used in this iteration.
    Bind every result to its evaluated demand and cage revisions.
    Record evaluated state and separately record proposed next state.
    If analysis inputs changed, return the existing analysis-request route.
    If proposed input is unchanged and all required consumers are complete,
        finalise the evaluated stable state.
    If a semantic state repeats, record a cycle without claiming convergence.
    Otherwise invalidate affected consumers and carry required constraints.
At the iteration limit, finalise that explicit termination condition.
```

The semantic state hash excludes iteration counters, timestamps, and random revision tokens. Convergence requires stable cage/factor/scope state, finite quantities, all required evaluations at the same revisions, and valid methods. The same cage can remain selected after increased demands if its complete re-evaluation succeeds. A fixed point is a software condition; engineering acceptance is a separate conclusion about its results.

If the finite family has no feasible candidate, report that family-specific result. Enlarged sections, a different system, a richer cage family, or changed analysis assumptions are new scenarios. Geometry, stiffness, mass, connectivity, releases, and load changes require renewed analysis lineage. A cage-only iteration may reuse raw demand only when the selected analysis model permits that separation. Retain deterministic candidate ordering, tie-breaks, iteration limits, and cycle handling. Missing instances remain in the expected ledger.

## 11 Qualify spectral PMM and downstream demand methods

### 11.1 Statistical response is not a concurrent vector

Response-spectrum P, M2, M3, and shear extrema generally do not occur simultaneously. Label separate component bounds accordingly; do not present (Nmax, M2max, M3max) as a signed physical time state. Choose a declared code-design method, a qualified conservative bound, or a genuine signed-time route. [N6]

Build expected combinations from request/role catalogue, members from the physical roster, and cuts from independent inventory. Bind every required minimum/maximum component once. An interval midpoint (upper + lower)/2 and half-width (upper − lower)/2 are representations of that interval; they are not automatically gravity and a concurrent earthquake vector.

### 11.2 Conditions for an eight-corner box

Construct B = [Nmin,Nmax] × [M2min,M2max] × [M3min,M3max] with one source/cut/cage lineage. The eight vertices are bounding scenarios, not native simultaneous force states.

If the fixed-cage three-dimensional capacity set K is convex and all vertices of the untransformed box belong to K, then B belongs to K. The premises require evidence for the actual resistance representation. A computed convex hull that overestimates resistance does not establish conservative capacity.

When demand transformation T depends nonlinearly on N, EI, magnification, minimum eccentricity, alpha, or another quantity, testing only T at the eight original vertices does not prove T(B) is contained in K. Supply an analytical monotonicity/bounding proof on the whole interval, a verified interval enclosure, or subdivided domains with certified bounds and error budgets. A few interior samples are diagnostic, not a proof over the continuum. Identify singular denominators and discontinuous method branches explicitly.

A box wholly within proven resistance establishes the stated conservative result. An outside corner establishes failure of that sufficient bound, not proof that the physical structure experiences that corner. Refine the qualified design method or source description before turning a bound failure into a claimed concurrent-load failure.

### 11.3 Consumer-specific qualifications

A PMM component box does not determine a storey equilibrium or the governing SCWB axial load. Define direction-compatible N scenarios and their capacity-selection rule separately. Storey effects use the common physical cut and full population, with per-mode aggregation before modal combination where required. Do not derive alpha from an arbitrary shear attached to a PMM vertex.

The spectral method record binds cases, modes, active damping, correlation, applied eccentricity, directional combination, vertical effects, R/D/I, native scales, capacity assumptions, nonlinear bounds, governing-N policy, and independent examples. The priority example in the appendix follows these stages explicitly and leaves actual-source and general nonlinear proofs visible.

## 12 Design walls and coupling beams

### 12.1 Physical wall and analysis results

Define physical segments, storeys, openings, boundary regions, and connected wall legs. A pier label is a result-grouping key; verify whether its shells represent one physical wall. Establish axes and transfer for L, T, and U sections. Do not add shell, pier, and section-cut results as duplicate loads.

At each critical level, bind N, M, and V to one cut, reference, action, and side. Distinguish wall length lw, thickness bw, total height Hw, storey height, and critical-region height. Include basement transitions, foundation faces, openings, section changes, transfer storeys, and wall terminations.

### 12.2 Axial force and flexure

Apply the correct thickness and aspect-ratio rules. Compute N–M capacity with actual vertical and boundary reinforcement. Boundary regions include dimensions, concentrated bars, confinement, and compressive-strain requirements, not only a total steel area. Evaluate required earthquake signs and axial states.

Generate the critical wall height and design moment envelope from the applicable Hw/lw and structural-system branch. Do not copy one base or pier maximum indiscriminately up the wall. Link laps, bar reduction, shear design, and confinement to the critical region. [N1, 7.6]

### 12.3 Shear and sliding interfaces

Derive design shear from analysis shear, the specified capacity/demand moment ratio, dynamic amplification, and code bounds, all at the same wall and design revision. Use the existing or explicitly unmapped shear owner for web reinforcement and concrete contribution; evaluate interaction and crushing limits separately.

Treat a construction joint, wall base, or other sliding surface as an interface check with area, roughness, friction coefficient, compatible normal force, and bars crossing and anchored across the interface. A concrete shear resistance result does not establish sliding resistance. Proposed ratios and actual crossing bars are distinct.

### 12.4 Coupling beams and system contribution

Select conventional or diagonal reinforcement from the applicable span/depth and shear branch. Solve bar area, angle, confinement, wall anchorage, and constructability together. A short coupling beam requires the appropriate deep-member mechanism. Check the axial-force couple transferred to wall legs against system overturning equilibrium.

Compute wall overturning and applicable shear participation at one direction, base reference, and seismic method. Transform local moments and include r × F when references differ. If system participation changes the permitted R/D class, revise the building analysis profile; reinforcement enlargement alone does not settle that system decision.

## 13 Design slabs and diaphragms

### 13.1 Slab model and reinforcement

Classify one-way, two-way, beam-supported, flat, ribbed, waffle, transfer, or raft slabs from support and span geometry. Include openings, cantilevers, thickness changes, drops, capitals, and column/wall connections. A rigid diaphragm assumption describes in-plane kinematics and does not replace vertical flexure or punching design.

Read shell forces and moments with local axes, faces, and units. m11, m22, and m12 are per-unit-width effects. For strip or patch design, record width, load path, and integration rule. Distribute twisting moments by an independently qualified method. Handle numerical singularities through a physical averaging/integration basis, not arbitrary deletion of high values.

At every face and reinforcement direction, evaluate flexure, minimum area, spacing, cover, span/support distribution, cut-offs, and anchorage. Use service combinations for immediate/long-term deflection and cracking with explicit cracking, creep, shrinkage, stiffness, and construction-stage assumptions.

### 13.2 Punching

Construct physical critical perimeters around columns or concentrated loads, accounting for edges, corners, openings, and column shape. Compute effective perimeter, depth, area, and reference centre from actual geometry and reinforcement layers. Subtract the compatible load inside the perimeter when deriving net punching demand.

Include transferred moments with the selected critical-perimeter stress method. Retain moment-sharing or reduction factors, concrete resistance, permitted punching reinforcement, maximum resistance, outer perimeter, and anchorage checks as distinct quantities. A vertical-force-only ratio is insufficient when moment transfer applies. [N2, Chapter 8; applicable TBDY slab branch]

### 13.3 Diaphragm load path

Trace inertia forces into vertical resisting elements through diaphragm shear, chords, collectors, opening boundaries, transfer regions, and connections. Bind each collector demand to its wall/frame node and anchorage region. In semi-rigid models, reconcile integrated membrane forces with compatible global storey effects.

For transfer slabs, use an appropriate deep-member or strut-and-tie model for vertical load transfer. Combine its detailing requirements with the separate diaphragm action set. For flat slab–column systems, include the applicable interaction of drift, moment transfer, and punching resistance.

## 14 Design foundations and the soil interface

### 14.1 Geotechnical basis

Bind stratigraphy, groundwater, bearing resistance parameters, settlement properties, liquefaction, and seismic ground conditions to the geotechnical report. Allowable pressure, characteristic resistance, design resistance, and subgrade stiffness are different quantities and must not collapse into one soil-capacity scalar. Record method, edition, and applicable foundation family. [N1, Chapter 16]

Define isolated, strip, combined, raft, or piled foundations with levels, geometry, pedestals, tie beams, embedment, water pressure, and drainage. Separate superstructure and foundation models require an explicit transfer interface and compatible action families.

### 14.2 Load transfer

Transfer the full six-component base force state to the physical foundation reference using axes and r × F. Preserve total axial, horizontal shear, bending, and torsion for each compatible case/combination. Add foundation self-weight, soil, water, and other foundation loads separately without duplicating source loads. Geotechnical, structural ULS, and service families remain distinct.

### 14.3 Contact and soil checks

For a qualified rigid-footing full-contact model, q = N/A ± Mx/Wx ± My/Wy. If tension appears, solve the no-tension contact region and equilibrium or use the selected soil–structure model. Report contact area, extrema, resultant location, and equilibrium residual.

Evaluate bearing, sliding, overturning, uplift, and overall stability with the declared load/resistance format. Compute total and differential settlement from service demands and soil deformation properties. Subgrade modulus is a calibrated model parameter, not bearing capacity. Check mesh sensitivity and equilibrium for spring models.

### 14.4 Structural foundation design

Create critical flexural, one-way shear, and punching cuts at the required column/wall/pile locations. Use declared raft strips or patches. Design both faces/directions with minima, anchorage, starter bars, continued wall boundaries, local bearing, ties, and joint geometry.

For piles, separate axial/bending/lateral response, group effects, cap stiffness and deep-member behaviour, pile–cap anchorage, and inertial/kinematic seismic actions. Geotechnical pile resistance/settlement and structural section/cap design remain separate owners with a common action and revision interface.

## 15 Route every TBDY family through explicit product profiles

The 17 TBDY chapters define different design bases, analysis methods, materials, and special systems. A full product profile identifies the applicable methods and owners; it does not treat all chapters as reinforced-concrete PMM. The following preserves the previous full-engine scope without claiming that these owners are implemented in the inspected snapshot.

| TBDY chapter | Profile responsibility | Principal result concept |
| --- | --- | --- |
| 1 General provisions | Project type, scope, responsibility | Project design basis |
| 2 Ground motion | Hazard, site spectrum, record target | Seismic hazard model |
| 3 Building characteristics | Classes, performance, irregularity | Building classification |
| 4 Strength-based design | Modelling, analysis, directional effects, drift, second order | DGT design actions |
| 5 Deformation-based design | Nonlinear response and deformation acceptance | Performance assessment |
| 6 Nonstructural components | Floor acceleration, component force, displacement, anchorage | Component and anchor design |
| 7 Cast-in-place concrete | Frames, walls, joints, slabs, detailing | RC design |
| 8 Precast concrete | Connections, erection, diaphragm, system behaviour | Precast design |
| 9 Steel | Stability, members, connections, ductile mechanisms | Steel design |
| 10 Light-gauge steel | Thin-wall buckling, panels, fasteners | Light-gauge design |
| 11 Masonry | In-plane/out-of-plane walls, ties, detailing | Masonry design |
| 12 Timber | Material direction, members, joints, diaphragms | Timber design |
| 13 Tall buildings | Design stages and performance targets | Tall-building assessment |
| 14 Isolated buildings | Property bounds, displacement, upper/lower structure, tests | Isolation assessment |
| 15 Existing buildings | Knowledge level, actual properties, damage, retrofit | Existing-building assessment |
| 16 Ground and foundations | Soil, foundations, piles, interaction | Foundation assessment |
| 17 Simplified design | Full applicability assessment before the simplified route | Simplified-design result |

### 15.1 Performance and existing structures

Start from measured properties, knowledge level, actual reinforcement, section behaviour, hinge/distributed-plasticity models, effective stiffness, cyclic laws, and limit states. Select pushover or nonlinear response history only within its allowed conditions. Record selection/scaling of paired horizontal and required vertical records, damping, and integration parameters.

Check convergence, equilibrium, and energy residuals; failed steps cannot disappear from an extreme-value calculation. Distinguish ductile deformations from brittle shear/joint actions. Combine element results under the applicable building-performance rule. Retrofit creates new geometry/material/connection revisions and the required new analysis generation.

### 15.2 Other materials and special systems

Steel requires section classification/local buckling, member strength/stability, connection design, and ductile system capacity design. Light-gauge steel adds the selected effective-section/direct-strength route, distortional buckling, panels, and fasteners. Timber adds material orientation, moisture/duration, joint ductility, net sections, and diaphragm transfer. Masonry combines openings, gravity, in-plane shear/flexure, out-of-plane response, ties, and layout. Each uses its own code package and independent examples.

Precast design includes connection stiffness/capacity, erection, continuity, diaphragm, and system classification. Tall buildings carry separate design-stage scenarios. Isolation includes property bounds, bidirectional response, torsion, stability, displacement clearance, services, and device tests. Nonstructural components require their actual floor acceleration/displacement and physical connection. Unmapped implementations remain visible rather than being represented by a concrete solver or an empty passing control.

## 16 Turn the catalogue into explicit calculation contracts

### 16.1 Rule cards and mappings

Each rule records identity/version, normative edition/clause, applicability, physical grain, inputs and units, actual inspected owner, explanatory algorithm, branches/exceptions, output, dependencies, tolerances, examples, and invalidation conditions. Keep source wording, interpretation, and implementation decisions distinguishable. Formula ownership remains singular.

Preserve the 73 source identities: five SRC identities and 68 engineering identities. Do not invent CHK-008 or renumber the list. CHK-108 denotes A3 plan projections; CHK-111 denotes B3 vertical structural discontinuity. Crosswalks depend on meaning, not numeric resemblance. DAG nodes and the historical 242 atomic candidates remain separate catalogues.

`CHECK_MAPPING.json` distinguishes inspected snapshot owners from the inaccessible local tree. Every verified function/path has a full source commit and content hash. A partial owner supports only the described quantity. If no implementation is verified, use `UNMAPPED`; for the unreviewed local source use `NOT_INSPECTED`. A named concept in this recipe is not sufficient evidence for a mapping.

### 16.2 Instances and result algebra

A project control instance binds rule revision, physical subject, required cut/face, combination/step, direction/sign, and method profile. Keep a stable logical identity across iterations and a separate evaluation/revision identity for each execution.

Separate execution, applicability, engineering verdict, evidence quality, and release role. A proven exceedance may coexist with an unresolved dependency. Derive independent summary flags for proven failure, unresolved evidence, complete expected evaluation, and satisfaction of required criteria. Do not hide one fact under the other.

Numerical results include value, limit, ratio where meaningful, equation/terms, units, governing state, source hash, method, candidate revision, and numerical residual. Qualitative checks contain a measurable predicate and evidence. None, NaN, infinity, or an empty list is not a successful result.

### 16.3 Complete-population accounting

Construct expected set E from physical scope and applicability and observed set O from execution. Record E minus O, O minus E, duplicate identities, and disjoint status partitions. Count physical members, combination pairs, cuts, evaluated instances, and satisfied instances separately. The denominator cannot be derived from only calculable or passing rows.

Method validation qualifies an owner over its declared domain with independent examples. Project validation then establishes that this version consumed the correct source, scope, and revisions. It does not require a new hand calculation for every repeated instance, nor does it waive project source completeness.

## 17 Retain one pipeline and explicit dependencies

### 17.1 Existing ownership

The inspected `engineering/pipeline.py::EnginePipelineRunner` remains the production entry owner for Web and CLI. The existing source adapters, dependency service, mixed-demand service, alpha iteration, snapshot, and receipt responsibilities remain in place. Offline banks and archived scenarios must use those same production owners through qualified adapters. Exact source bindings belong to `CHECK_MAPPING.json`.

### 17.2 Planning contract

Each stage declares produced and consumed artifacts, schemas, dimensions, source/generation, scope, and design/method revisions. Planning verifies single producer, missing producer, and cycles. The target contract schedules ordinary dependencies topologically and treats feedback as one bounded iteration component. This is a required integration behaviour, not a claim that the inspected registry already schedules the whole catalogue. Provenance and execution graphs serve different purposes.

| Artifact concept | Producer responsibility | Consumer |
| --- | --- | --- |
| Source snapshot | Existing live/offline adapters | Source derivations |
| Physical topology and cut inventory | Geometry and source owners | Demands, face transfer, scope, joints |
| Analysis qualification | Model, load, and analysis checks | Design-demand compilation |
| Typed design demand | Combination and transformation owners | Member and global calculations |
| Bound candidate/selected design | Candidate evaluator | Capacity, end resistance, detailing |
| End capacity state | Existing section capacity owner | SCWB, joints, capacity shear |
| Joint and storey results | Shared joint/storey owners | Iteration and finalisation |
| Complete result ledger | Expected-instance execution | Run aggregation |
| Finalised run result | Snapshot and receipt owners | Web, CLI, reports, replay |

### 17.3 Validity and partial execution

Schema identity alone does not establish validity. Check units, source generation, physical scope, method authority, and cage revision. Cache keys must cover these dependencies; identical member names or demand maxima are not sufficient. Every planned instance produces a terminal execution record, including an explicit missing-dependency result. Independent branches may continue while affected consumers remain unresolved.

### 17.4 Preparation and calculation sequence

The complete flow is project/role profile → native catalogue read → expected combinations → definition/assignment difference → selected mutation plan and readback → any required analysis and generation binding → scope-driven force/topology acquisition → actual or candidate cage binding → global/local effects and capacity → SCWB/Ve/panel/alpha → affected design iteration → one finalised result.

After preparation or reanalysis, rebind selection to the current model, catalogue, and generation before force capture. Keep preparation, capture, and design as distinct operations under the existing orchestrator. They are conceptual operation boundaries, not claims that three new commands have been implemented. Opening a report or replaying an old run must not mutate ETABS.

### 17.5 Getter and setter acceptance scenarios

The 12 adapter examples specify: empty catalogue; partially complete catalogue; same name with different definition; success return with incorrect readback; repeat idempotency; state restoration on success/error/cancel; missing direction or internal-joint side; changed P–Delta generation; cage-dependent invalidation; shared-property isolation; partial transaction recovery; and save/reopen/readback consistency.

These fixtures define expected behaviour. Live acceptance requires an installed-version round trip on a controlled model through the existing gateway. Offline fixture matches do not establish native COM behaviour.

## 18 Produce buildable reinforcement

Evaluate coordinates, layers, corner/intermediate restraints, tie/crosstie topology, bends, hooks, laps, anchorage, cover, clear spacing, and concrete placement. Sufficient nominal area does not resolve bar clashes at a joint.

Separate three search levels: cages within a fixed section; section/material alternatives within one system; and system/layout/span/foundation alternatives. Declare which analysis inputs each level changes. A geometry or stiffness change cannot be concluded by a local PMM recalculation alone.

Store constraints separately from objectives such as steel quantity, concrete volume, diameter standardisation, and labour. User policy supplies priorities or weights. A least-steel claim applies to the candidate family actually searched; accumulated constraints do not prove a global optimum. Record tried candidates, rejection reasons, search limits, governing demands, tie-breaks, and selected cage. Engineering approval and overrides create explicit new states and preserve the calculation history.

## 19 Separate verification evidence

### 19.1 Six reporting levels

| Level | Evidence required | What it does not establish |
| --- | --- | --- |
| Document and schema consistency | Schema validation, stable IDs, foreign keys, source hashes, coverage and declared ownership checks | Numerical or engineering correctness |
| Independent example arithmetic | Independent fixed calculations, expected values, units, justified tolerances, residuals | Execution of production owners |
| Actual YENI owner comparison | Verified production call, mapped inputs, returned quantity, owner/dependency hashes, comparison result | Full-source pipeline or live acquisition |
| Recorded-source pipeline replay | Frozen input, actual existing runner execution, complete sealed output inventory and replay comparison | New live capture or engineering approval |
| Live ETABS source validation | Existing-session native reads/writeback where applicable, return codes, readback, source generation and expected census | Independent method acceptance |
| Engineering acceptance | Named scope, accepted methods, normative applicability, complete required evidence, authorised disposition | Automatic closure merely from document delivery |

Use `NOT_RUN` for an unexecuted level in the current delivery. Keep historical command/result records under their original versions and dates. The 73 primary examples, 44 protected production comparisons, 333 recipe assertions, and separate 333 PDF V2 comparisons are never substituted for each other.

### 19.2 Verification dimensions within a level

Preserve the earlier recipe's five technical dimensions: units/signs/identity; formula arithmetic; numerical solver quality; member/joint interaction; and a complete building/iteration/report chain. These dimensions describe test content, whereas the six levels above describe the kind of execution and authority demonstrated.

Use analytical unit/axis/reference-transfer cases; independent axial/eccentricity/Euler/tie/alpha/punching calculations; independent integration and root/angle convergence; a complete bound member/joint example; and a frozen building with scope, design iteration, sealed result, and report comparison. Thousands of low-level assertions do not replace a complete integration example.

### 19.3 Independence and discriminating tests

Record each oracle's source, derivation, physical assumptions, code lineage, independent portions, and tolerances. Importing the production function from another module does not create an independent oracle. Copies of one oracle in different repositories are one lineage. Closed-form calculations, independent integration, or fully specified printed examples may provide independence within their stated idealisations.

Test 90-degree axis transformations, sign reversal for genuinely symmetric cages, unit invariance, and mesh/angle convergence. Establish a mathematical monotonicity property before relying on it; more reinforcement does not make every coupled check monotonically better.

On source copies, remove a whole member, one combination, one element side, or one required cut. Expected population remains unchanged and affected dependencies remain visible. Change a policy or cage and verify the correct capacity/result/report identities change. Include a case with both a proven exceedance and missing evidence; both facts must survive aggregation.

### 19.4 Complete iteration witness

Freeze a small model with geometry, materials, actions, cages, and identities. Include an active 0.70 < alpha < 1 branch, rather than only alpha = 1. Trace Mr, SCWB, shear population, alpha, amplified M/V, candidate response, EI/Nk, PMM, Ve, and panel equilibrium wherever independently supplied data support those quantities. A declared capacity input is identified as such and is not represented as a solved physical RC section.

The priority-chain fixture supplied with this revision completes its declared modal-to-alpha arithmetic contract using common identities and explicit capacity-input assumptions. Its missing actual-model inputs and more general spectral proofs remain listed. It grants no physical section or building acceptance.

Distinguish a cage-policy change using the same qualified source from a stiffness/section change requiring new analysis. Compare reports projected from one sealed result with calculators disabled. Source, method, policy, or plan changes must be visible in replay comparisons.

## 20 Save results and generate engineering reports

### 20.1 One final result

The finalised result binds project basis, source/generation, methods/policies, plan, expected scope, all instance results, selected designs, iteration history, and evidence manifest. Persist the actual R08/R10/R14 and related outputs in the same inventory. Reports consume those stored results. Legacy archive compatibility remains explicitly versioned.

Record code commit or dirty-tree fingerprint, interpreter/dependencies, configuration, and numerical policy. Separate semantic hashes from incidental path/timestamp metadata. Byte integrity and numerical equivalence are different comparisons. `IDENTICAL` requires the declared complete inventory and payload equality, not only unchanged early-stage receipts.

### 20.2 Reading order

Present project/design basis, model and source, analysis/global checks, member designs, joints/storeys, walls/slabs/foundations, iteration, and verification. State scope and overall disposition before detailed rows. Show physical ID with the user's label and storey.

Each calculation page presents the physical subject and useful diagram, clause, inputs/units, equation/intermediate values, governing action/cut, value and limit, selected reinforcement, decision/reason, and source/revision. Distinguish signed states from component envelopes. Show a positive physical reason for any exemption.

### 20.3 Report contents

| Section | Required information |
| --- | --- |
| Basis | Editions, method, R/D/I, building classes, site, performance |
| Model/source | Physical inventory, mesh/faces, generation, hashes |
| Analysis | Mass, modes, spectrum/scales, irregularities, drift, second order, equilibrium |
| Columns/beams | Actual cages, PMM/flexure, Ve/shear, confinement, placement, service, anchorage |
| Joints/storeys | SCWB terms, panel equilibrium, alpha, target members |
| Walls/coupling beams | Boundary/web reinforcement, capacity shear, overturning contribution |
| Slabs/diaphragms | Strip reinforcement, punching, deflection, collectors/chords, connections |
| Foundations | Transfer, contact, geotechnical and structural results, piles |
| Iteration | Evaluated/proposed demand, cage changes, stable selection reason |
| Calculation appendix | Every expected instance, intermediate values, method and source references |

Generate drawings from the same selected DesignModel used by tables: column cages/crossties, beam bars/tie zones, wall boundaries, slab strips, and foundation reinforcement. Quantity take-off additionally uses actual lengths, bends, and lap policy.

## 21 Operate reproducible scenarios

The operator chooses the profile and source. The existing runner validates identity/inventory, shows expected scope, executes the registered plan and supported iteration, and seals a result. The user can inspect governing members/cuts and create a separate policy scenario without altering raw evidence.

Use offline sources to develop repeatable methods. Live acquisition fills the same concrete data contract once the required fields and model changes are known. Compare scenarios by source, edition, method, plan, policy, cages, governing state, capacities, and decisions, not only maximum utilisation.

Implement vertical slices in dependency order: source/design basis; global analysis effects; section kernel; members; joints/storeys/iteration; walls/slabs/foundations; special profiles; final result/report. Each slice needs actual inputs, an independent example, the existing production owner, and a report field. A control name or passing shell is not a completed calculation.

## 22 Preserve the worked interpretation examples

These examples retain their own source models and precision. They are not calculations for the user's live model. Spreadsheet cells and printed reports provide stated inputs and arithmetic; their overall compliance labels are not imported as YENI verdicts.

### 22.1 Rectangular column units and axes

For the declared teaching section t2 = 400 mm, t3 = 600 mm, fck = 30 MPa, gamma_c = 1.5, and compression N = 1500 kN, Ac = 240000 mm² and fcd = 20 MPa. The TS 500 gross-area limit is 4320 kN and the TBDY limit 2880 kN, with ratios 0.34722 and 0.52083 if N belongs to each control's own required action role.

M2 uses e_min = 33 mm and M3 uses 27 mm, giving minimum moments 49.5 and 40.5 kNm. A square section would not expose a swapped-axis error. The one-percent area is 2400 mm²; 12 bars of 16 mm provide approximately 2412.74 mm². That arithmetic alone says nothing about complete PMM, second-order, spacing, ties, shear, or anchorage acceptance.

### 22.2 Drift and global second order

In source GE-S04, physical PDF page 18, lambda = 0.3999 with effective drift 44.91 mm over 4500 mm gives 0.003991; 67.65 mm in Y gives 0.006012. The source's selected branch compares against 0.008. On page 19, average relative drift 4.85 mm, cumulative weight 2050.03 tf, shear 187.26 tf, and height 4.50 m give theta = (0.00485 × 2050.03)/(187.26 × 4.50) = 0.011799. This is a storey quantity, distinct from local member beta.

### 22.3 Area and actual cage

Source GE-S05 reports S1(D-4), 30 × 30 cm, minimum area 9.00 cm², and 4 bars of 18 mm. Their area is 10.1788 cm² and ratio 1.1310 percent. Required area, selected area, and actual bars remain distinct, and the same candidate identity must feed PMM and transverse checks. Material or force data from another source model cannot complete this example silently.

### 22.4 SCWB and storey amplification

Source GE-S14, S8, gives column capacities 10.96 + 11.47 = 22.43 and beam capacities 12.89 + 7.24 = 20.13 in the source's moment unit. The raw inequality 22.43 ≥ 1.2 × 20.13 = 24.156 is false; any exemption needs separate physical evidence.

The source's storey totals 39.21/43.21 give alpha_ratio = 0.9074288 and demand_amplification = 1.1020148. The source labels the inverse as Alpha-i; the canonical fields distinguish them. The other direction's 39.19/51.21 gives approximately 0.7652802 and inverse 1.306711. Directional factors are not interchangeable.

### 22.5 End capacity and shear

Source GE-S04, PDF page 72, SB201, gives upper/lower end moments 34.70 and 19.85 tfm and ln = 3.90 m. The mechanism shear is 13.9872 tf. The same table separately gives the amplified-combination shear 22.16 tf, reinforced resistance 90.65 tf, and concrete-section upper limit 170.91 tf. Preserve all four meanings and the branch selecting the final comparison.

### 22.6 Spreadsheet cell trace

In GE-S06, DRIFT_KONTROL!G5 gives lambda = 0.341/0.761 = 0.4480946124. DATA!D2 is the raw drift ratio 0.0015402558; with R = 7 and I = 1, DRIFT_KONTROL!D8 is 0.0107817907. The selected limit 0.008/lambda is 0.0178533724 and utilisation approximately 0.60390779. Keep worksheet/cell, source hash, meaning, unit, and rule together.

### 22.7 Punching and foundation reinforcement

Source GE-S04, PDF page 106, SB301, shows transferred moments and critical-perimeter properties in addition to vertical force. The reported maximum stress is 77.98 tf/m² against 130.32 tf/m², approximately 0.5984. The full geometry and intermediate terms are needed to qualify the method.

The separate GE-S18 foundation source uses 25 mm bars at 200 mm: 24.5437 cm²/m. Tie this area to flexure, minimum reinforcement, and detailing within that source model. Its geotechnical or load data cannot be imported into another building example.

### 22.8 Independent section references

The earlier Column reference includes a 400 × 600 mm section at N = 500 kN, 4-bar and 6-bar 20 mm cages, and angular comparisons at 72, 144, and 288 divisions. A separate Column-Engine hand-resultant fixture examines compression-block intersection with actual bar disks. Its three-bar arrangement is a mathematical integration example, not a proposed code-compliant cage.

Retain each example's material idealisation, net-concrete definition, units, and tolerance. Independence follows calculation lineage, not repository name. These earlier reference results remain historical unless their commands are rerun and recorded for this delivery.

## 23 Data and decision dictionary

| Field | Meaning | Rule |
| --- | --- | --- |
| source_id | Immutable acquired package | May remain fixed across a design-policy change |
| generation_id | Analysis generation producing results | Renew after analysis-affecting change |
| physical_id | Physical built object | Independent of mesh and cage revisions |
| cut_id | Analysis side and physical reference | Rounded position alone is insufficient |
| state_key | Source, case/combination, step, and cut | Keep compatible components together |
| candidate_id | Concrete section and bar arrangement | Not merely an area |
| method_id | Formula, normative branch, numerical policy | Revise after a method interpretation change |
| alpha_ratio | Vis/Vik | Distinct from its inverse |
| demand_amplification | Absolute factor for a defined target | Apply once to immutable base demand |
| Nk_euler | Euler load from EI and effective length | Not the foundation tie-beam symbol |
| Nk_tie_beam | Relevant connected-column/wall axial load | Input to the applicable TBDY 16.13 demand |
| gamma_shear_axial | TS 500 axial-force coefficient in shear | Select compression/tension branch |
| gamma_punch_capacity | Punching resistance reduction | Not automatically compounded with moment sharing |
| gamma_f_moment_share | Share of transferred moment carried by flexure | Complement acts through perimeter shear |
| evaluated_demand_hash | Demand actually consumed by stored results | Must agree across final consumers |
| proposed_demand_hash | Next-iteration demand | Not a final evaluated result until consumed |

Align schemas and owner adapters with these meanings. Record human interpretations and overrides with reasons; free text does not replace numerical source data. Link rule cards, examples, and production comparisons through a versioned method binding.

## 24 Source roles and traceability

### 24.1 YENI and the inherited recipe

The master handoff dated 14 November 2026 and the previous 18 November recipe are preserved by hash in the source manifest and in the private evidence package. The 24-chapter organisation, 73 identities, original worked quantities, and method distinctions remain traceable through the preservation index. Current implementation statements refer only to the inspected published commit identified at the start of this document.

YENI code establishes inspected owner and data-flow evidence. The published CURRENT_STATE and VERIFICATION_LEDGER provide historical observations with their own original commits and commands. They do not establish that the inaccessible local tree is unchanged or that their historical executions were rerun here.

### 24.2 Normative and manufacturer references

N1 is TBDY 2018, represented by the inspected GE-S09 source and its official public publication reference. N2 is the supplied TS 500 February 2000 edition with the included T1/T2 amendments, GE-S16. The formula appendix records physical PDF and printed-page locators separately.

N3 denotes CSI combination operator documentation; N4 the FrameForce interface; N5 output stations; N6 response-spectrum semantics and aggregation; N7 initial P–Delta; N8 native design-combination selection; N9 result selection; N10 combination lifecycle; N11 the combination interface and GetCaseList; N12 SetCaseList; N13 model lock; and N14 linear-static stiffness-source selection. The public manifest supplies manufacturer URLs and inspected/documented version limits. Older API documentation is not proof that the same tuple or editable-table schema is active in the installed ETABS version.

### 24.3 Reference repositories

The earlier read-only TBDY, Column, and Column-Engine reference files provide alternative contracts and independent calculation lineage. Their pinned commits and file hashes remain in the source manifest/private provenance record. Their runtimes and historical process instructions do not become production owners for YENI.

### 24.4 Example reports and workbooks

The golden source registry preserves report, workbook, source-hash, physical-page/cell, and atlas references. Original Word/Excel/PDF files and access links are private evidence. Source reports illustrate traceable calculations; their global pass labels are not adopted as YENI acceptance. The previous workbook review covered eight workbooks and 38 sheets with 34 selected arithmetic comparisons; that is historical scope, not a new execution claim.

The worked-example bank distinguishes SOURCE_RECALC, SOURCE_REPORTED, DERIVED_BENCHMARK, and CONTRACT_FIXTURE. Scenario coverage explicitly states positive, negative, boundary, and missing-source cases; absent scenarios remain open. Appendices below present the same machine-readable records in a readable form. Source identities and the six verification levels govern every claim in those appendices.


## Appendix A — The 73 control cards and existing owners


This appendix preserves the 73 existing recipe labels and their three method steps. It adds typed inputs, applicability, independent physical scope, verified source owners and remaining integration work. No CHECK identifier is added. These are recipe labels, not counts of tests, DAG nodes or accepted physical instances.

### Inspected source boundary

The inspected published snapshot is `feridunfc/YENI` at `b255c3030c09c88a17bbec766fc2bb22682ad027`, tree `9cf5b99059cd107a1e447c398fd1e93b7292b31b`, on the published `baseline/local_import` branch. The user-reported local commit `a2e26b664d9b2b217e828de2c1df0c3df26068b1` and its unfinished changes are **NOT_INSPECTED**; every local owner binding is **UNMAPPED**. The source paths below describe only the published snapshot. No code equivalence or history relationship is inferred.

The registry contains 22 stages and binds 30 distinct nodes of a 94-node catalog. 44 recipe labels have at least one identified partial implementation or source binding; 29 have no calculation owner for their requested scope. The number 44 is a mapping cardinality and is unrelated to the historical 44 production comparisons. None of these counts proves engineering acceptance.

### Shared data and execution contract

- **Source identity:** Every consumed artifact retains source/model identity, analysis generation and method revision; these are distinct fields.
- **Units:** Declared dimensional quantities are converted once. A native unit or force-sign convention is never inferred from magnitude or a column heading alone.
- **Signs axes:** Normalize native axial force to compression-positive N explicitly. Preserve signed local M2/M3 and their section axes; do not equate local 2/3 to major/minor labels. Global transforms require captured axes.
- **Demand semantics:** Signed concurrent vectors, static Linear Add results, scalar spectrum envelopes and conservative interval bounds remain different types. Spectral Max/Min components are not a physical concurrent state.
- **Reinforcement:** Template, proposed, algorithm-selected, engineer-approved and as-built states are distinct. Capacity, SCWB, shear and detailing consume the same identified cage and demand revision.
- **Execution:** Formula and signature text is documentation only. No eval/exec, second solver, second pipeline or new ETABS attachment route is specified. Production binding calls the existing owner after explicit unit/identity adaptation.
- **Verification:** A mapped source symbol establishes implementation location only. It is not a runtime test, engineering acceptance, or proof that the inaccessible local tree has the same implementation.

Input names below define an English recipe contract. They are not automatic keyword mappings to the inspected Python signatures. The machine mapping includes the exact source symbol, line range, full commit, Git blob identity and SHA-256 for every owner. Formula text is explanatory. Independent benchmark arithmetic remains separate from the existing production owner.

For each card, engineering prerequisites are data/evidence relationships, not new runtime DAG edges. Continue through the existing runner and registration owner. A check may share a source prerequisite with another check without defining a second execution engine.

### SRC-001 — Archive and source integrity

**Scope:** Source package and each manifest entry. **Golden example:** `GE-SRC-001` (CONTRACT_FIXTURE).

#### Specification and applicability

- **YENI engineering source and integration contract, Existing 73-card recipe, 2026-11-18.** Engineering integration contract. Every imported or captured source used by a check; operational validity is separate from engineering compliance.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `source_package_id` | Immutable source package identity / not_applicable | Identity and revision are exact; no numeric coercion. Source: Imported package. |
| `manifest` | Versioned expected paths, byte sizes and file digests / not_applicable | Identity and revision are exact; no numeric coercion. Source: Independent archive manifest. |
| `file_size_bytes` | File byte size / byte | Nonnegative physical magnitude; retain the declared unit. Source: Physical archive bytes. |
| `file_sha256` | SHA-256 digest per entry / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical archive bytes. |

**Engineering prerequisites:** Direct source/contract inputs above.

#### Preserved implementation recipe

1. Read the versioned manifest and match every declared entry to its physical file.
2. Recompute file sizes and digests; check uniqueness of package paths and names.
3. Retain every entry result under one source-package receipt.

**Output:** Verified package identity, file inventory and per-entry integrity result.

**Acceptance:** The file list, sizes, digests, schema and origin reconcile with the complete expected inventory.

**Expected instance key:** `source_package_id`, `manifest_path`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/native_archive.py::NativeArchive._verify` | Archive member, digest, size and subset-manifest validation. |

**Registered stages:** `column-bank`. **Existing GAP references:** `GAP-004`, `GAP-017`.

**Inspected implementation:** The native-bank reader validates its explicit complete/subset archive contract.

**Remaining work:** Map each live/import format to its existing integrity entry point; inspect the target local revision before binding it.

**Negative scenario to preserve:** Change one byte or remove one manifest entry; the package must not remain an accepted source.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-SRC-001` preserves example provenance and coverage.

### SRC-002 — Model identity and units

**Scope:** Model snapshot and capture transaction. **Golden example:** `GE-SRC-002` (CONTRACT_FIXTURE).

#### Specification and applicability

- **YENI engineering source and integration contract, Existing 73-card recipe, 2026-11-18.** Engineering integration contract. Every imported or captured source used by a check; operational validity is separate from engineering compliance.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `model_identity` | Process/model/path/content identity / not_applicable | Identity and revision are exact; no numeric coercion. Source: Existing ETABS session. |
| `units_before` | Native force, length and temperature units / not_applicable | Identity and revision are exact; no numeric coercion. Source: Existing ETABS getter. |
| `selected_results_before` | Selected cases and combinations / not_applicable | Identity and revision are exact; no numeric coercion. Source: Existing ETABS getter. |
| `capture_transaction` | Before/after/error-path state record / not_applicable | Identity and revision are exact; no numeric coercion. Source: Existing session owner. |

**Engineering prerequisites:** `SRC-001`.

#### Preserved implementation recipe

1. Record model identity and user state at the start of the existing single connection transaction.
2. Read with an explicit unit contract and preserve the same process/model binding throughout capture.
3. Restore prior units and selections on success, error and cancellation; record before and after state.

**Output:** Model identity, unit contract and capture-transaction receipt.

**Acceptance:** Model/process identity and initial/final units and selections are evidenced on every exit path.

**Expected instance key:** `capture_transaction_id`, `process_id`, `model_identity`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/live_etabs.py::_with_etabs` | Existing attachment/session boundary. |
| `src/tbdy_next/etabs_source_gateway_windows.py::get_results_setup_state` | Read current result-selection state. |
| `src/tbdy_next/etabs_source_gateway_windows.py::restore_results_setup_state` | Restore result-selection state. |

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-004`.

**Inspected implementation:** The existing ETABS session and selection-state helpers are present; this is capture infrastructure before registered calculation stages.

**Remaining work:** Qualify complete force/length/temperature unit restoration and all success/error/cancellation paths. No live transaction was executed here.

**Integration note:** Preserved recipe step 3 requires prior-unit restoration. Pinned AGENTS.md records explicit user authorization to set kN/m/C on connection (API code 6), while requiring restoration of temporary output/pattern/mode selections. Reconcile the active capture policy during local integration: a permitted persistent unit change is not a restoration failure; every temporary selection must still be restored and verified. No live setter/getter was executed here.

**Negative scenario to preserve:** Interrupt capture with an error; restore user state and reject results carried from a different model.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-SRC-002` preserves example provenance and coverage.

### SRC-003 — Complete frame result population

**Scope:** Physical frame and required result key. **Golden example:** `GE-SRC-003` (CONTRACT_FIXTURE).

#### Specification and applicability

- **YENI engineering source and integration contract, Existing 73-card recipe, 2026-11-18.** Engineering integration contract. Every imported or captured source used by a check; operational validity is separate from engineering compliance.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `physical_frame_roster` | Expected physical frames independent of returned forces / not_applicable | Identity and revision are exact; no numeric coercion. Source: Geometry capture. |
| `analysis_element_map` | Object-to-element chain and oriented end joints / not_applicable | Identity and revision are exact; no numeric coercion. Source: Captured frame and joint connectivity. |
| `expected_case_family` | Selected and required design cases/combinations / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved ComboBook definitions, extracted before result evaluation; this input does not require SRC-005 arithmetic replay. |
| `required_cuts` | Object station, element ID, element station and side / m | Coordinates are oriented I-to-J; two element sides at one joint remain distinct. Source: Independent connectivity, coordinates, station assignments and offsets. |
| `observed_force_rows` | Physical signed force state / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |

**Engineering prerequisites:** `SRC-002`, `SRC-004`.

#### Preserved implementation recipe

1. Classify columns, beams, null/rigid lines and other frames from the physical roster.
2. Bind each physical object to all required analysis elements and result keys.
3. Full-outer-join expected and observed keys; count each physical object once.

**Output:** Expected frame-result inventory and element/cut coverage ledger.

**Acceptance:** Every expected element and result group has a unique match to independently obtained physical and analytical geometry.

**Expected instance key:** `physical_unique_id`, `combination_id`, `object_station_m`, `analysis_element_id`, `element_station_m`, `element_side`, `step_identity`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/column_pmm.py::bind_pmm_mesh_source` | Bind physical columns to captured frame analysis elements. |
| `src/tbdy_next/engineering/column_pmm.py::bind_configured_output_cuts` | Bind independently located cuts within the supported configured subset. |
| `src/tbdy_next/engineering/column_pmm.py::_required_cut_coverage` | Compare required element-side cuts with observed rows. |

**Registered stages:** `column-pmm`. **Existing GAP references:** `GAP-005`, `GAP-006`.

**Inspected implementation:** PMM v6 supports a configured required-cut subset including internal element sides.

**Remaining work:** A complete independent physical cut census, other station/offset branches and the general 73-check instance ledger remain separate requirements.

**Integration note:** The inspected required-cut implementation has a qualified configured subset, including the supported Min Stations = 3, oriented element-chain and offset branches. This is not proof of a complete independently prescribed native cut census or TS 500 free length.

**Negative scenario to preserve:** Remove every force row for one physical column; that column and its expected denominator must remain visible.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-SRC-003` preserves example provenance and coverage.

### SRC-004 — Analysis generation binding

**Scope:** Model content and analysis generation. **Golden example:** `GE-SRC-004` (CONTRACT_FIXTURE).

#### Specification and applicability

- **YENI engineering source and integration contract, Existing 73-card recipe, 2026-11-18.** Engineering integration contract. Every imported or captured source used by a check; operational validity is separate from engineering compliance.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `model_parameter_revision` | Demand-affecting model parameters and file identity / not_applicable | Identity and revision are exact; no numeric coercion. Source: Source capture. |
| `analysis_case_settings` | Initial state, P-delta, modal and damping settings / not_applicable | Identity and revision are exact; no numeric coercion. Source: Native case definitions. |
| `analysis_generation` | Generation and completion/convergence evidence / not_applicable | Identity and revision are exact; no numeric coercion. Source: Native analysis provenance. |
| `result_generation` | Generation of each consumed result family / not_applicable | Identity and revision are exact; no numeric coercion. Source: Source result provenance. |

**Engineering prerequisites:** `SRC-002`.

#### Preserved implementation recipe

1. Record model content, file digest, case settings and generation evidence separately.
2. Bind every consumed result family to the analysis generation and case settings that produced it.
3. Turn post-analysis demand-affecting changes into versioned validity decisions.

**Output:** Analysis-generation binding and source validity of design demand.

**Acceptance:** Accepted evidence binds the consumed results to the same model-parameter generation.

**Expected instance key:** `model_identity`, `analysis_generation`, `case_id`, `result_family`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/analysis_setup.py::audit_model_analysis_setup` | Audit model/case/P-delta generation prerequisites. |
| `src/tbdy_next/vs05_d4_source_authority.py::audit_d4_source_authority` | Review source authority and case/combination provenance. |

**Registered stages:** `analysis-setup`. **Existing GAP references:** `GAP-003`, `GAP-008`.

**Inspected implementation:** Generation-related prerequisites and explicit source-authority findings are recorded.

**Remaining work:** Bind accepted analysis-generation evidence to every design result; a lock flag, file digest or matching name is insufficient.

**Negative scenario to preserve:** Supply changed model parameters with a locked-model flag; lock state or filename alone must not establish freshness.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-SRC-004` preserves example provenance and coverage.

### SRC-005 — Combination definitions and arithmetic replay

**Scope:** Combination syntax node and case/cut/step. **Golden example:** `GE-SRC-005` (CONTRACT_FIXTURE).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 4.4.2.1; 4.4.3.2; 4.4.4.1; equations 4.9, 4.10, 4.11. Reinforced-concrete strength combinations; the example declares S=H=0 and uses the approximate vertical-earthquake branch only outside the special vertical analysis scope of 4.4.3.1. Operator semantics and project roles remain explicit.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `combination_graph` | Typed operators, children and roles / not_applicable | Identity and revision are exact; no numeric coercion. Source: Native combination definitions and approved ComboBook. |
| `combination_coefficients` | Signed child coefficients / 1 | Signs and operator order are retained; no replacement of Envelope by Linear Add. Source: Native graph. |
| `constituent_states` | Physical signed force state / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `SDS` | Short-period design spectral coefficient / 1 | Nonnegative physical magnitude; retain the declared unit. Source: Approved hazard profile. |

**Engineering prerequisites:** `SRC-002`, `SRC-003`, `SRC-004`.

#### Preserved implementation recipe

1. Resolve an acyclic combination graph and retain each operator and child role.
2. For Linear Add, sum the six components with their coefficients only under compatible state semantics; retain other operators as their own types.
3. Store independent replay residuals together with operator lineage and the physical-concurrency classification.

**Output:** Typed combination demand, replay residuals and operator provenance.

**Acceptance:** Supported operators and coefficients reproduce independent replay values while envelope semantics remain explicit.

**Expected instance key:** `combination_id`, `operator_node`, `physical_cut_key`, `step_identity`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/mixed_demands.py::linear_coefficients` | Resolve supported native graph expressions into exact coefficients. |
| `src/tbdy_next/engineering/mixed_demands.py::earthquake_partition` | Decompose qualified signed seismic contributions. |
| `src/tbdy_next/column_engine/spectral_envelope.py::replay_component_envelope` | Replay scalar component envelopes without asserting concurrency. |

**Registered stages:** `analysis-setup`, `mixed-demand-components`. **Existing GAP references:** `GAP-002`, `GAP-007`, `GAP-018`.

**Inspected implementation:** Supported signed Linear Add and same-source scalar spectral component replay have existing owners.

**Remaining work:** Complete operator/role scope, expected design families and modal/torsional qualification; keep scalar envelopes distinct from physical signed states.

**Negative scenario to preserve:** Present an Envelope or SRSS result as a signed Linear Add vector; downstream consumers must reject the type substitution.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-SRC-005` preserves example provenance and coverage.

### CHK-001 — Concrete strength lower bound

**Scope:** Assigned concrete material and structural role. **Golden example:** `GE-CHK-001` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.2.5.1. Applicable new reinforced-concrete members and actually assigned concrete classes.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `used_material_assignments` | Actual member/material roster / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical assignments. |
| `fck` | Characteristic cylinder strength / MPa | Nonnegative physical magnitude; retain the declared unit. Source: Assigned concrete material. |
| `applicable_profile` | Structure and seismic design profile / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved project profile. |

**Engineering prerequisites:** `SRC-002`.

#### Preserved implementation recipe

1. Derive used concrete materials from member assignments and remove duplicate material identities.
2. Select the applicable minimum-strength branch for each material and project profile.
3. Compare fck with that limit and reference every affected physical member.

**Output:** Minimum-strength result by material and affected-member list.

**Acceptance:** Every used concrete material is checked against the correct applicable lower bound.

**Expected instance key:** `material_id`, `assigned_member_id`, `structural_role`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/next_checks.py::_material_items` | Assigned concrete fck >=25 MPa scalar screening. |

**Registered stages:** `material-a1`. **Existing GAP references:** `GAP-001`.

**Inspected implementation:** In-use concrete material screening is implemented with source-unit conversion.

**Remaining work:** Confirm applicability and complete actual material/member assignment scope at the local revision.

**Negative scenario to preserve:** Assign an unsuitable material to one member; checking an unused compliant material must not hide the violation.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-001` preserves example provenance and coverage.

### CHK-002 — Concrete strength range and method applicability

**Scope:** Assigned concrete material and structural-system profile. **Golden example:** `GE-CHK-002` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.1.3; 7.2.5.3(a). Applicable Chapter 7 material class and the separately supported constitutive-method domain.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `used_material_assignments` | Actual member/material roster / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical assignments. |
| `fck` | Characteristic cylinder strength / MPa | Nonnegative physical magnitude; retain the declared unit. Source: Assigned concrete material. |
| `applicable_profile` | Structure and seismic design profile / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved project profile. |
| `constitutive_method` | Supported material-model revision and domain / not_applicable | Identity and revision are exact; no numeric coercion. Source: Existing section calculation owner. |

**Engineering prerequisites:** `SRC-002`.

#### Preserved implementation recipe

1. Evaluate only materials actually used by the project.
2. Select the normative material class and calculation-method domain for each material.
3. Record upper-bound and applicability decisions with edition, clause and method revision.

**Output:** Material applicability decision and method-domain classification.

**Acceptance:** Upper strength limits and method ranges are traced to the used material and applicable rule.

**Expected instance key:** `material_id`, `structural_role`, `constitutive_method_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/source_control_bundle.py::concrete_upper_subcondition` | fck <=80 MPa scalar upper bound. |
| `src/tbdy_next/source_control_bundle.py::_concrete` | Bind the scalar bound to used-material source evidence. |

**Registered stages:** `report-evidence`. **Existing GAP references:** `GAP-001`.

**Inspected implementation:** The scalar upper bound and material binding exist.

**Remaining work:** Complete the chosen system/method applicability beyond the scalar upper bound.

**Negative scenario to preserve:** Supply strength outside the supported range; do not round it into a permitted class.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-002` preserves example provenance and coverage.

### CHK-003 — Minimum column cross-section dimensions

**Scope:** Column section and geometry revision. **Golden example:** `GE-CHK-003` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.3.1.1. Actual column shape and seismic system; rectangular and circular limits are separate branches.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `section_dimensions` | Physical section dimensions / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `section_shape` | Rectangle, circle or explicit supported shape / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical section assignment. |
| `applicable_profile` | Column role and seismic system / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved profile. |

**Engineering prerequisites:** `SRC-003`.

#### Preserved implementation recipe

1. Normalize native and local section dimensions exactly once.
2. Derive the controlling short side, diameter or other measure for the actual section shape.
3. Compare that measure with its applicable limit and bind the result to the section revision.

**Output:** Column geometry result with measured value, limit and section identity.

**Acceptance:** Actual dimensions of every supported section shape are compared with the correct geometric criterion.

**Expected instance key:** `column_unique_id`, `section_revision`, `shape_branch`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/quick_checks.py::evaluate_geometry_capture` | Assigned rectangular column short-side screening. |

**Registered stages:** `geometry`. **Existing GAP references:** `GAP-001`, `GAP-005`.

**Inspected implementation:** The supported rectangular-column numerical dimension check exists.

**Remaining work:** Other section shapes and full normative applicability require explicit supported branches and evidence.

**Negative scenario to preserve:** Swap unequal rectangular dimensions or omit one dimension; a square-section assumption must not provide acceptance.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-003` preserves example provenance and coverage.

### CHK-004 — TBDY column axial compression limit

**Scope:** Column and applicable earthquake design combination. **Golden example:** `GE-CHK-004` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.3.1.2. Applicable earthquake design combinations, complete Ndm population and compression-positive demand.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `Ac` | Gross concrete area / mm^2 | Nonnegative physical magnitude; retain the declared unit. Source: Physical section geometry. |
| `fck` | Characteristic concrete strength / MPa | Nonnegative physical magnitude; retain the declared unit. Source: Assigned material. |
| `seismic_axial_states` | Physical signed force state / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `ductile_combination_roles` | Applicable earthquake design family / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved ComboBook. |

**Engineering prerequisites:** `SRC-003`, `SRC-004`, `SRC-005`, `CHK-001`, `CHK-003`.

#### Preserved implementation recipe

1. Build the applicable earthquake combination family from the approved role book.
2. Determine the required compression demand from all necessary cuts and states.
3. Calculate Ndm/(0.40 fck Ac) in consistent units and retain every demand and the governing key.

**Output:** TBDY axial-limit result and governing demand identity.

**Acceptance:** The correct Ndm population, Ac and fck produce a recorded result over the full expected scope.

**Expected instance key:** `column_unique_id`, `ductile_combination_id`, `physical_cut_key`, `step_identity`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/ts500_column.py::section_axial_limits_kn` | Compute the 0.40 fck Ac limit. |
| `src/tbdy_next/engineering/column_gates.py::evaluate_axial_caps` | Evaluate explicit axial demand against caps. |
| `src/tbdy_next/engineering/column_live_gates.py::_axial_gates` | Project caps with assigned seismic roles. |

**Registered stages:** `column-gates`. **Existing GAP references:** `GAP-001`, `GAP-002`, `GAP-008`.

**Inspected implementation:** The numerical cap and role-dependent projection are implemented.

**Remaining work:** Qualify the complete governing seismic Ndm population, combination roles and source generation.

**Negative scenario to preserve:** Delete a seismic combination and leave gravity only; the remaining scope must not establish overall compliance.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-004` preserves example provenance and coverage.

### CHK-005 — TS 500 column axial compression limit

**Scope:** Column and TS 500 design load state. **Golden example:** `GE-CHK-005` (SOURCE_RECALC).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 7.4.1; equations 7.7. Axial compression limit for an applicable column design state; it excludes reinforcement contribution and is separate from PMM capacity.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `Ac` | Gross concrete area / mm^2 | Nonnegative physical magnitude; retain the declared unit. Source: Physical section geometry. |
| `fcd` | Concrete design strength / MPa | Nonnegative physical magnitude; retain the declared unit. Source: Assigned fck and applicable material factor. |
| `axial_design_states` | Physical signed force state / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |

**Engineering prerequisites:** `SRC-003`, `SRC-004`, `SRC-005`, `CHK-001`, `CHK-003`.

#### Preserved implementation recipe

1. Normalize compression sign and select the applicable design states.
2. Compute Nd/(0.90 fcd Ac) as the normative axial-demand limit.
3. Keep this comparison separate from raw PMM axial capacity and retain every required state.

**Output:** TS 500 axial-limit result, independent of the raw PMM capacity value.

**Acceptance:** Correct Nd and material factors reproduce the axial limit as a separate design criterion.

**Expected instance key:** `column_unique_id`, `design_combination_id`, `physical_cut_key`, `step_identity`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/ts500_column.py::section_axial_limits_kn` | Compute the 0.90 fcd Ac limit. |
| `src/tbdy_next/engineering/column_axial.py::evaluate_column_axial` | Evaluate required column/combination axial scope. |

**Registered stages:** `column-axial`, `column-gates`. **Existing GAP references:** `GAP-002`, `GAP-005`, `GAP-008`.

**Inspected implementation:** The normative cap is distinct from raw N0 and is evaluated over the axial ledger.

**Remaining work:** Qualify all applicable load states and generation; preserve this cap as a separate result from PMM.

**Negative scenario to preserve:** Use Nd above the normative cap while raw N0 remains larger; a low PMM ratio must not hide this violation.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-005` preserves example provenance and coverage.

### CHK-006 — Modal mass participation

**Scope:** Modal case and horizontal direction. **Golden example:** `GE-CHK-006` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 4.8.1.2; equations 4.30. Each applicable modal case and horizontal earthquake direction; retain individually significant modal contributions.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `modal_case` | Case, generation and eigensolution identity / not_applicable | Identity and revision are exact; no numeric coercion. Source: Modal source. |
| `modal_mass_ratios` | Individual and cumulative direction participation / 1 | Each mode has one identity. X and Y remain distinct; do not combine different modal cases. Source: Native modal participation rows. |
| `required_cumulative_ratio` | Applicable cumulative threshold / 1 | Nonnegative physical magnitude; retain the declared unit. Source: Normative branch. |
| `individual_significance_ratio` | Applicable individual-mode threshold / 1 | Nonnegative physical magnitude; retain the declared unit. Source: Normative branch. |

**Engineering prerequisites:** `SRC-004`.

#### Preserved implementation recipe

1. Read an ordered and unique mode set from one analysis generation.
2. Determine cumulative participation and modes that must individually be included in each direction.
3. Evaluate all applicable participation requirements and freeze the consumed mode population.

**Output:** Modal participation result, mode inventory and directional comparisons.

**Acceptance:** Every required mode and direction is assessed under the selected participation rule.

**Expected instance key:** `modal_case_id`, `horizontal_direction`, `mode_id`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/modal.py::evaluate_modal_mass` | 0.95 directional participation and individually significant mode list. |

**Registered stages:** `modal`. **Existing GAP references:** `GAP-018`.

**Inspected implementation:** Directional modal participation arithmetic is implemented.

**Remaining work:** Qualify modal source population, active damping and method applicability; this scalar check does not establish modal force aggregation.

**Negative scenario to preserve:** Remove the Y direction or an individually significant mode; sufficient X participation must not qualify the full model.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-006` preserves example provenance and coverage.

### CHK-007 — Initial PMM and reinforcement candidate

**Scope:** Column section, demand state and candidate cage. **Golden example:** `GE-CHK-007` (SOURCE_REPORTED).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 6.2.5; 7.1. Supported reinforced-concrete section equilibrium and strain compatibility with a single physical signed demand state and identified candidate cage.
- **Turkish Building Earthquake Code (TBDY), 2018.** 7.3.2. Column candidate reinforcement must satisfy the applicable seismic detailing scope separately from numerical PMM capacity.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `section_dimensions` | Physical section dimensions / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `selected_cage` | Actual or explicitly selected reinforcing cage / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `demand_state` | Physical signed force state / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `section_method` | Stress block, steel model and strain limits / not_applicable | Identity and revision are exact; no numeric coercion. Source: Existing section owner. |

**Engineering prerequisites:** `SRC-003`, `SRC-004`, `SRC-005`, `CHK-004`, `CHK-005`, `CHK-009`, `CHK-115`.

#### Preserved implementation recipe

1. Construct the section and candidate cage in the same geometry and axis system.
2. Call the existing strain-compatibility calculation owner for capacity and solver residuals in the demand direction.
3. Record the candidate numerical result, reinforcement role and required downstream assessments.

**Output:** First-order PMM candidate result, capacity point, residual and cage identity.

**Acceptance:** The same signed demand and explicit candidate reproduce an independent reference calculation; the reference remains a verification artifact.

**Expected instance key:** `column_unique_id`, `physical_cut_key`, `combination_id`, `step_identity`, `candidate_cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/section_capacity.py::solver` | Existing section-capacity solver factory. |
| `src/tbdy_next/engineering/column_pmm.py::evaluate_column_pmm` | Initial signed station PMM binding and evaluation. |

**Registered stages:** `column-pmm`. **Existing GAP references:** `GAP-006`, `GAP-010`, `GAP-011`.

**Inspected implementation:** A strain-compatibility PMM owner and source-bound station evaluation exist.

**Remaining work:** Retain candidate status and complete the full cut/load/cage/second-order acceptance scope.

**Negative scenario to preserve:** Combine axial force and moments from different cases or cuts; no concurrent design state may be produced.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-007` preserves example provenance and coverage.

### CHK-009 — Column longitudinal ratio and reinforcement role

**Scope:** Column cage role and revision. **Golden example:** `GE-CHK-009` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.3.2.1. Column longitudinal reinforcement; normal region and lap-splice branches are distinct. A template is not a selected cage.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `Ac` | Gross section area / mm^2 | Nonnegative physical magnitude; retain the declared unit. Source: Physical section. |
| `selected_cage` | Actual or explicitly selected reinforcing cage / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `reinforcement_role` | TEMPLATE, PROPOSED, SELECTED or actual / not_applicable | Identity and revision are exact; no numeric coercion. Source: Explicit design binding. |
| `region_type` | Normal, lap or other applicable region / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical longitudinal region ledger. |

**Engineering prerequisites:** `SRC-003`, `CHK-003`.

#### Preserved implementation recipe

1. Classify reinforcement as template, algorithmic candidate, approved design or observed existing reinforcement.
2. Calculate As from the physical bars and compute As/Ac.
3. Evaluate applicable minimum and maximum limits on the same cage role and revision.

**Output:** Reinforcement-ratio result, source role and selected-cage reference.

**Acceptance:** Bar geometry determines area and ratio; template evidence and selected-design decisions remain distinguishable.

**Expected instance key:** `column_unique_id`, `longitudinal_region`, `cage_revision`, `reinforcement_role`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/column_gates.py::evaluate_reinforcement_state` | Role-aware bar area and ratio decisions. |
| `src/tbdy_next/engineering/rebar_selection.py::select_column_rebar` | Select supported column cages with the 0.01 Ac floor. |

**Registered stages:** `column-gates`, `column-r10`. **Existing GAP references:** `GAP-011`.

**Inspected implementation:** Template/selected roles and supported candidate ratio bounds are explicit.

**Remaining work:** Establish approved/actual cage provenance and complete physical detailing and anchorage.

**Negative scenario to preserve:** Relabel a below-minimum selected cage as a template; the known violation or identity conflict must remain visible.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-009` preserves example provenance and coverage.

### CHK-010 — Story drift source feature

**Scope:** Story, earthquake case and direction. **Golden example:** `GE-CHK-010` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 4.9.1.1. Reduced interstory displacement or source drift ratio with an explicit dimensional contract.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `source_drift` | Source drift ratio or relative displacement / explicitly 1 or m | The field dimension is declared before conversion. X/Y and signed state identity are retained. Source: Source schema and drift rows. |
| `story_height` | Physical story height / m | Nonnegative physical magnitude; retain the declared unit. Source: Story geometry. |
| `joint_displacements` | Compatible top/bottom displacements, where available / m | Same case, step, diaphragm and direction. Source: Joint result source. |

**Engineering prerequisites:** `SRC-003`, `SRC-004`, `SRC-005`.

#### Preserved implementation recipe

1. Resolve whether the source field is displacement, displacement ratio or absolute displacement.
2. When needed, derive same-case/same-direction interstory displacement from upper and lower levels.
3. Store a drift feature with definition, unit, position and case provenance.

**Output:** Typed story-drift feature with derivation lineage.

**Acceptance:** Drift definition, dimensions, story height and case origin are established.

**Expected instance key:** `physical_story_id`, `direction`, `case_id`, `eccentricity_sign`, `step_identity`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/story_drift_binding.py::bind_story_drift` | Bind captured drift evidence. |
| `src/tbdy_next/story_delta.py::calculate` | Calculate typed story displacement differences. |

**Registered stages:** `story-drift`. **Existing GAP references:** `GAP-004`, `GAP-005`, `GAP-018`.

**Inspected implementation:** Typed source drift and same-source displacement derivations exist.

**Remaining work:** Qualify complete direction/eccentricity/case scope and keep displacement and ratio units distinct.

**Negative scenario to preserve:** Supply absolute displacement as interstory difference, or a drift ratio as a length; dimensional validation must reject it.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-010` preserves example provenance and coverage.

### CHK-011 — Design spectrum reconstruction

**Scope:** Spectrum function, project basis and analysis method. **Golden example:** `GE-CHK-011` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 2.3.4; 4.2.1; 4.4.1; equations 2.2, 2.3, 4.1, 4.8. Approved hazard, soil, earthquake level, structural system and period branch; coefficients in g and physical acceleration are distinct.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `SDS` | Short-period normalized spectral coefficient / 1 | Nonnegative physical magnitude; retain the declared unit. Source: Approved hazard profile. |
| `SD1` | One-second normalized spectral coefficient / 1 | Nonnegative physical magnitude; retain the declared unit. Source: Approved hazard profile; evaluate the prescribed numerical period convention in seconds. |
| `T` | Spectral sample period / s | Nonnegative physical magnitude; retain the declared unit. Source: Selected period or native function points. |
| `TL` | Long-period transition / s | Nonnegative physical magnitude; retain the declared unit. Source: Approved code profile. |
| `system_coefficients` | R, D and I / 1 | The selected structural system and direction define the coefficients. Source: Approved system profile. |
| `spectrum_scales` | Function units, case scale and later demand scale / not_applicable | Identity and revision are exact; no numeric coercion. Source: Native function/case definitions. |

**Engineering prerequisites:** `SRC-004`.

#### Preserved implementation recipe

1. Build the piecewise spectrum functions from the approved project parameters.
2. Calculate Sae, Ra and SaR at the relevant periods.
3. Compare independently reconstructed values with ETABS function samples, retaining units and applied scales.

**Output:** Design-spectrum feature, scaling information and pointwise residual table.

**Acceptance:** Spectrum and reduction branches reconcile with independent point calculations and the model scale.

**Expected instance key:** `earthquake_level`, `direction`, `function_id`, `sample_period_s`, `scale_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/spectrum_reconstruction.py::review_spectrum_reconstruction` | Reconstruct and compare spectrum function samples. |

**Registered stages:** `vs04-source`. **Existing GAP references:** `GAP-001`, `GAP-018`.

**Inspected implementation:** Independent spectrum-function reconstruction exists within its input assumptions.

**Remaining work:** Bind the approved hazard/soil/system profile and distinguish function scale, case scale and later design scaling.

**Negative scenario to preserve:** Mix acceleration in g with dimensional acceleration, or change the earthquake level; the prior result must become invalid.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-011` preserves example provenance and coverage.

### CHK-101 — Seismic mass and weight reconstruction

**Scope:** Mass source, load role and story. **Golden example:** `GE-CHK-101` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 4.5.9; Table 4.3. Physical story seismic mass and applicable live-load participation; native self-mass and additional mass must not be counted twice.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `story_loads` | Individual story G and Q contributions / kN | Individual story weight is not cumulative weight; self-mass is counted once. Source: Native mass-source and physical load ledger. |
| `participation_factors` | Applicable live-load participation by use / 1 | Use the applicable occupancy branch; do not infer from load-pattern names. Source: Approved use classification. |
| `gravity_acceleration` | Weight-to-mass conversion / m/s^2 | Nonnegative physical magnitude; retain the declared unit. Source: Declared unit convention. |
| `native_mass_source` | Self/additional/load-mass settings and assignments / not_applicable | Identity and revision are exact; no numeric coercion. Source: Native source definitions. |

**Engineering prerequisites:** `SRC-003`, `SRC-004`.

#### Preserved implementation recipe

1. Record every mass contribution and whether material self-mass is included.
2. Assemble G+nQ and other approved contributions over stories/objects without duplication.
3. Reconcile story and building totals with source mass/reaction references on one unit basis.

**Output:** Mass ledger, story weights and balance residuals.

**Acceptance:** G+nQ, self-mass and assigned additional mass are counted exactly once in the same model.

**Expected instance key:** `physical_story_id`, `mass_source_revision`, `load_component`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/basis_linkage.py::_mass` | Reconcile observed mass-source/weight quantities within role-book evidence. |

**Registered stages:** `vs04-source`. **Existing GAP references:** `GAP-001`, `GAP-003`.

**Inspected implementation:** Mass and role-book source linkage is present.

**Remaining work:** Complete a physical per-story mass ledger with self-mass/additional-mass/load contributions and accepted G+nQ scope.

**Negative scenario to preserve:** Include self-weight both as material mass and load-pattern mass; the independent balance must identify double counting.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-101` preserves example provenance and coverage.

### CHK-102 — Directional modal period selection

**Scope:** Modal case, direction and building height. **Golden example:** `GE-CHK-102` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 4.7.3.2; 4.7.3.3; 4.7.3.4; 4.8.1. Directional natural periods and method-specific equivalent-load period restrictions are separate quantities.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `modal_periods` | T, f and angular frequency by mode / T: s; f: Hz; omega: rad/s | Mode identity is exact; direction comes from participation, not mode number. Source: Modal output. |
| `directional_participation` | X/Y modal participation / 1 | Same case and generation as modal periods. Source: Modal output. |
| `building_height` | Applicable seismic height / m | Nonnegative physical magnitude; retain the declared unit. Source: Approved physical story scope. |
| `period_policy` | Method-specific system and empirical coefficients / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved profile. |

**Engineering prerequisites:** `CHK-006`, `CHK-011`.

#### Preserved implementation recipe

1. Normalize period and frequency fields according to their physical dimensions.
2. Select the governing mode in each earthquake direction using a recorded rule.
3. Evaluate any applicable empirical-period or method-specific restrictions separately.

**Output:** Directional design period, selected-mode lineage and applicable limit result.

**Acceptance:** Mode selection and empirical-period restrictions have distinct traceable evidence.

**Expected instance key:** `modal_case_id`, `direction`, `period_consumer_method`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/analysis_numerics.py::_periods` | Verify period/frequency/omega arithmetic. |
| `src/tbdy_next/basis_linkage.py::_spectrum_modal` | Bind modal/spectrum settings and directional context. |

**Registered stages:** `vs04-source`. **Existing GAP references:** `GAP-001`, `GAP-018`.

**Inspected implementation:** Period arithmetic and spectrum/modal source linkage are implemented subscopes.

**Remaining work:** Qualify directional dominant-mode selection and the appropriate empirical-period policy for each consumer.

**Negative scenario to preserve:** Use a model with reversed modal directions; assuming mode 1 is X and mode 2 is Y must fail the selection test.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-102` preserves example provenance and coverage.

### CHK-103 — Equivalent lateral force base shear

**Scope:** Building, earthquake direction and equivalent-load method. **Golden example:** `GE-CHK-103` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 4.7.1; 4.7.2; 4.7.3; equations 4.19, 4.22, 4.23. Equivalent lateral force method only where permitted by the project system, height and irregularity profile.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `story_mass_height` | Individual mass/weight and height / mass: tonne; weight: kN; height: m | Height reference and weight conversion are explicit; retain physical story order. Source: Mass and geometry features. |
| `design_period` | Applicable equivalent-load period / s | Nonnegative physical magnitude; retain the declared unit. Source: CHK-102. |
| `spectrum_and_system` | Demand ordinate and R,D,I / ordinate: explicit g or m/s^2; coefficients: 1 | Convert acceleration once; match horizontal direction. Source: CHK-011. |

**Engineering prerequisites:** `CHK-011`, `CHK-101`, `CHK-102`.

#### Preserved implementation recipe

1. Select the applicable equivalent lateral force branch for the project profile.
2. Determine base shear from spectral demand and its normative minimum.
3. Distribute story forces and required roof contribution; verify resultant force and moment balance.

**Output:** VtE, story lateral forces and distribution-balance record.

**Acceptance:** Method applicability, base shear and story distribution agree with independent equilibrium.

**Expected instance key:** `building_id`, `direction`, `story_id`, `method_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/normative_basis.py::eq_4_19_equivalent_base_shear_kn` | Equivalent base-shear formula and minimum. |
| `src/tbdy_next/base_shear_screening.py::review_base_shear_screening` | Bind conditional source-screening quantities. |

**Registered stages:** `vs04-source`. **Existing GAP references:** `GAP-001`, `GAP-002`.

**Inspected implementation:** The equivalent base-shear formula and source screening are implemented.

**Remaining work:** Complete applicability, accepted period/mass and full story/roof force distribution and moment balance.

**Negative scenario to preserve:** Calculate a numerical value outside the method applicability range; it must not be promoted to normative acceptance.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-103` preserves example provenance and coverage.

### CHK-104 — Response spectrum base shear scaling

**Scope:** Spectrum case, direction and scale revision. **Golden example:** `GE-CHK-104` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 4.8.4.1; 4.9.1.1; equations 4.31. Response-spectrum force scaling with evidenced irregularity branch; drift consumers retain their own scaling policy. The A2/A3/B1-only gammaE branch question remains explicit.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `VtE` | Equivalent lateral base shear / kN | Nonnegative physical magnitude; retain the declared unit. Source: CHK-103. |
| `VtRS` | Same-case response-spectrum base shear / kN | Nonnegative physical magnitude; retain the declared unit. Source: Native compatible directional result. |
| `irregularity_profile` | A1/A2/A3/B1/B2/B3 and applicability / not_applicable | Identity and revision are exact; no numeric coercion. Source: Qualified irregularity features. |
| `existing_scale` | Native demand scale already applied / 1 | Nonnegative physical magnitude; retain the declared unit. Source: Source lineage. |
| `scale_revision` | One-time force transformation revision / not_applicable | Identity and revision are exact; no numeric coercion. Source: Demand owner. |

**Engineering prerequisites:** `CHK-103`, `CHK-106`, `CHK-107`, `CHK-108`, `CHK-109`, `CHK-110`, `CHK-111`.

#### Preserved implementation recipe

1. Bind the native spectrum case and direction and establish its existing source scale.
2. Calculate betaTE=max(1,gammaE VtE/VtRS) under the applicable gammaE branch.
3. Apply the required scaling once per demand revision and preserve before/after values.

**Output:** Response-spectrum scaling result and scaled-demand lineage.

**Acceptance:** Reference base shear, irregularity branch and pre/post scales reconcile in one run.

**Expected instance key:** `spectrum_case_id`, `direction`, `scale_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/normative_basis.py::eq_4_31_base_scale` | Numerical betaTE formula for the exposed branch inputs. |
| `src/tbdy_next/base_shear_screening.py::review_base_shear_screening` | Observe current and required spectrum scaling. |

**Registered stages:** `vs04-source`. **Existing GAP references:** `GAP-001`, `GAP-018`.

**Inspected implementation:** Numerical base-shear scaling exists for explicit branch inputs.

**Remaining work:** Adjudicate complete irregularity-branch applicability, including the preserved A2/A3/B1-only question; do not infer the no-irregularity branch from A1/B2/B3=False alone. Keep drift scaling policy distinct.

**Negative scenario to preserve:** Rescale already scaled results; duplicate amplification or unknown original scale must be rejected.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-104` preserves example provenance and coverage.

### CHK-105 — Effective interstory drift

**Scope:** Story, direction, earthquake case and infill connection class. **Golden example:** `GE-CHK-105` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 4.9.1.2; 4.9.1.3(a); equations 4.33, 4.34a. Applicable infill/connection branch, earthquake-level ratio and structural material factor; do not infer flexible connections.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `relative_displacement` | Reduced same-state interstory displacement / m | Nonnegative physical magnitude; retain the declared unit. Source: CHK-010. |
| `story_height` | Physical story height / m | Nonnegative physical magnitude; retain the declared unit. Source: Physical story ledger. |
| `drift_coefficients` | R/I, earthquake-level spectrum ratio and kappa / 1 | Use the displacement-specific period/scaling policy. Source: Approved profile and spectra. |
| `connection_class` | Infill/connection condition and evidence / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved architectural/structural detail. |

**Engineering prerequisites:** `CHK-010`, `CHK-011`, `SRC-005`.

#### Preserved implementation recipe

1. Calculate effective drift and the earthquake-level spectrum ratio using the applicable method.
2. Select the limit branch from evidenced infill and connection classification.
3. Compare every expected story/direction/case and retain the governing state.

**Output:** Effective-drift result and complete story/direction population.

**Acceptance:** Effective drift, spectrum ratio and connection-specific limit are compared over the same scope.

**Expected instance key:** `physical_story_id`, `direction`, `case_id`, `eccentricity_sign`, `connection_class`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/normative_basis.py::eq_4_34_effective_drift` | Conditional effective drift and connection-class limit. |
| `src/tbdy_next/effective_drift_readiness.py::review_effective_drift_readiness` | Review drift basis and expected evidence. |

**Registered stages:** `story-drift`, `report-evidence`. **Existing GAP references:** `GAP-001`, `GAP-005`, `GAP-018`.

**Inspected implementation:** The conditional effective-drift formula and readiness/source binding exist.

**Remaining work:** Qualify DD-level ratio, connection evidence, complete eccentricity population and displacement-specific scaling.

**Negative scenario to preserve:** Assign the more permissive limit without flexible-connection evidence; the applicability claim must remain unqualified.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-105` preserves example provenance and coverage.

### CHK-106 — A1 torsional irregularity

**Scope:** Story, direction and accidental-eccentricity family. **Golden example:** `GE-CHK-106` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** Table 3.6 A1; 3.6.2.1. Story/direction torsional irregularity under all required applied accidental-eccentricity cases.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `max_mean_drift` | Compatible maximum and mean story drift / both m or both 1 | Same case, direction and eccentricity; denominator must be physically valid. Source: Native drift population. |
| `eccentricity_family` | Both required applied eccentricity signs / not_applicable | Identity and revision are exact; no numeric coercion. Source: Case definitions and applied-effect proof. |

**Engineering prerequisites:** `CHK-010`, `SRC-005`.

#### Preserved implementation recipe

1. Construct the expected positive and negative eccentricity cases.
2. Calculate etaBi=DeltaMax/DeltaMean for each compatible state.
3. Record the irregularity classification and its analysis-method consequences separately.

**Output:** A1 irregularity feature and dependent method requirements.

**Acceptance:** Same-case drift ratios cover the complete required eccentricity family.

**Expected instance key:** `physical_story_id`, `direction`, `case_id`, `eccentricity_sign`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/next_checks.py::_a1_items` | Observed A1 ratios per story and direction. |

**Registered stages:** `material-a1`. **Existing GAP references:** `GAP-005`, `GAP-018`.

**Inspected implementation:** Observed maximum/mean drift ratios and source classification exist.

**Remaining work:** Qualify applied accidental-eccentricity effects and the complete positive/negative case family.

**Negative scenario to preserve:** Remove one eccentricity sign; a low ratio in the remaining sign must not complete the torsional scope.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-106` preserves example provenance and coverage.

### CHK-107 — A2 floor discontinuity

**Scope:** Story slab polygon and opening topology. **Golden example:** `GE-CHK-107` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** Table 3.6 A2 I/II/III; 3.6.2.2. Floor discontinuity includes geometric openings and force-transfer conditions; one ratio does not cover all branches.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `floor_polygons` | Floor and opening boundaries / m | One physical story plane; no double counted overlapping polygons. Source: Physical slab geometry. |
| `inplane_transfer_evidence` | Load-path and stiffness/strength evidence / not_applicable | Identity and revision are exact; no numeric coercion. Source: Qualified diaphragm model. |

**Engineering prerequisites:** `SRC-003`.

#### Preserved implementation recipe

1. Assemble floor polygons and openings in the same story plane.
2. Derive geometric discontinuity measures and required load-path conditions.
3. Assess each applicable geometric and analytical A2 branch separately.

**Output:** A2 geometry/transfer results and supporting polygons.

**Acceptance:** Floor continuity, openings and load transfer are evaluated under all applicable branches.

**Expected instance key:** `physical_story_id`, `floor_polygon_id`, `opening_id`, `A2_branch`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No A2 polygon/opening/load-path evaluator was found in the inspected source. Existing story-height readers are not this calculation.

**Negative scenario to preserve:** Lose a major opening polygon; assuming an unperforated gross floor must not close A2.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-107` preserves example provenance and coverage.

### CHK-108 — A3 plan protrusions

**Scope:** Story plan boundary and protrusion region. **Golden example:** `GE-CHK-108` (DERIVED_BENCHMARK).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** Table 3.6 A3; Figure 3.3; 3.6.2.2. Plan protrusions measured from the actual story boundary; this is not vertical discontinuity.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `plan_polygon` | Physical story boundary / m | Common story-plane axes and measured protrusion orientation. Source: Physical geometry. |
| `plan_dimensions` | Lx,Ly,ax,ay / m | Each protrusion dimension is paired with its actual plan direction. Source: Measured plan feature. |

**Engineering prerequisites:** `SRC-003`.

#### Preserved implementation recipe

1. Identify protrusion regions on the actual plan boundary.
2. Measure Lx/Ly and corresponding ax/ay in consistent directions.
3. Evaluate the A3 geometric branch and retain measured geometry references.

**Output:** A3 plan-protrusion result and dimensional references.

**Acceptance:** The correct plan polygon and story scope determine the A3 dimensional criteria.

**Expected instance key:** `physical_story_id`, `plan_region_id`, `plan_direction`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

Related source/catalog functions are retained without being counted as calculation owners:

- `src/tbdy_next/engineering/column_gates.py::resolve_legacy73_catalog_entry` — Correct A3 identity only; no plan calculation.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No plan-protrusion evaluator was found. The catalog alias correction is not a geometric implementation.

**Negative scenario to preserve:** Classify a plan protrusion as a vertical discontinuity; rule-identity validation must detect the incorrect mapping.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-108` preserves example provenance and coverage.

### CHK-109 — B1 weak story

**Scope:** Adjacent-story pair and horizontal direction. **Golden example:** `GE-CHK-109` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** Table 3.6 B1; 3.6.2.3. Adjacent-story effective shear areas by direction; infill geometry and permitted exceptions require evidence.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `effective_area_components` | Directional Aw,Ag,Ak by physical story / mm^2 | Project physical widths/areas to the declared direction; each member/infill counted once. Source: Column, wall and infill geometry. |
| `story_order` | Physical adjacent-story sequence / not_applicable | Identity and revision are exact; no numeric coercion. Source: Story geometry. |
| `infill_qualification` | Geometry, openings, height and applicable exceptions / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved infill evidence. |

**Engineering prerequisites:** `SRC-003`, `CHK-003`.

#### Preserved implementation recipe

1. Classify column, wall and infill contributions by actual geometry and structural role.
2. Construct Ae=Aw+Ag+0.15Ak in each direction without duplication.
3. Evaluate adjacent-story ratios and applicable exceptions in physical story order.

**Output:** B1 story/direction ratios and effective-area contribution ledger.

**Acceptance:** Directional effective areas are traceable to physical column, wall and infill evidence.

**Expected instance key:** `story_pair`, `direction`, `effective_area_component`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/weak_story_b1.py::evaluate_b1` | Directional effective-area and adjacent-story B1 arithmetic. |
| `src/tbdy_next/b1_source_bridge.py::evaluate_b1_sources` | Bind physical columns/walls/infill evidence. |

**Registered stages:** `report-evidence`. **Existing GAP references:** `GAP-001`, `GAP-005`.

**Inspected implementation:** Conditional B1 area arithmetic and physical-source binding exist.

**Remaining work:** Complete and approve infill geometry, opening/height assumptions, directionality and applicable exceptions.

**Negative scenario to preserve:** Infer infill area from a wall load pattern alone; missing physical geometry must prevent acceptance.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-109` preserves example provenance and coverage.

### CHK-110 — B2 soft story

**Scope:** Adjacent-story comparison, direction and same earthquake case. **Golden example:** `GE-CHK-110` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** Table 3.6 B2; 3.6.2.1. Both applicable neighboring-story drift/height comparisons under compatible earthquake states.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `mean_story_drift` | Same-state mean drift per story / m | Same case, direction, eccentricity and drift scale across neighbors. Source: CHK-010. |
| `story_heights` | Physical adjacent-story heights / m | Positive heights in physical elevation order. Source: Story geometry. |

**Engineering prerequisites:** `CHK-010`, `SRC-005`.

#### Preserved implementation recipe

1. Calculate mean drift divided by height for each story.
2. Perform both required neighbor comparisons in the correct physical story order.
3. Record B2 classification separately from the resulting analysis-method restrictions.

**Output:** B2 neighbor comparisons and method-applicability result.

**Acceptance:** Relevant neighbor ratios use compatible case data and drift/height quantities.

**Expected instance key:** `story_pair`, `neighbor_side`, `direction`, `case_id`, `eccentricity_sign`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/soft_story_b2.py::compare_adjacent` | Adjacent normalized-drift ratio. |
| `src/tbdy_next/soft_story_b2.py::bind_soft_story_b2` | Bind case/story/direction scope. |

**Registered stages:** `report-evidence`. **Existing GAP references:** `GAP-005`, `GAP-018`.

**Inspected implementation:** The adjacent-story B2 calculation and source binder exist.

**Remaining work:** Qualify all required neighbors, case/eccentricity combinations and derived analysis-method consequences.

**Negative scenario to preserve:** Mix earthquakes across neighbors or omit one neighbor; the soft-story population must remain incomplete.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-110` preserves example provenance and coverage.

### CHK-111 — B3 vertical structural discontinuity

**Scope:** Vertical load path and transfer joint. **Golden example:** `GE-CHK-111` (DERIVED_BENCHMARK).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 3.6.2.4(a); 3.6.2.4(b). Vertical discontinuity and supporting-member topology, including prohibition and special-analysis branches.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `member_joint_topology` | All incident 3D members and support roles / not_applicable | Identity and revision are exact; no numeric coercion. Source: Independent geometry/connectivity. |
| `vertical_load_paths` | Terminations and supporting members / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical topology derivation. |
| `special_analysis_evidence` | Applicable exception or mandated analysis / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved engineering method. |

**Engineering prerequisites:** `SRC-003`.

#### Preserved implementation recipe

1. Trace the upper and lower load-transfer path of each vertical member.
2. Classify transfer-beam, cantilever or other supporting-member conditions from geometry.
3. Evaluate the applicable B3 prohibition and special-analysis branches on the physical topology.

**Output:** B3 load-path result and topology evidence.

**Acceptance:** Three-dimensional connectivity and applicable exception conditions establish each B3 classification.

**Expected instance key:** `vertical_member_id`, `support_joint_id`, `vertical_load_path`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

Related source/catalog functions are retained without being counted as calculation owners:

- `src/tbdy_next/engineering/column_gates.py::resolve_legacy73_catalog_entry` — Correct B3 identity only; no vertical load-path calculation.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No full B3 vertical load-path classifier was found. Preserve the special-analysis requirements and prohibition branches as unimplemented mapping work.

**Negative scenario to preserve:** Ignore the missing lower support of a terminating column as missing data; the discontinuity must remain visible.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-111` preserves example provenance and coverage.

### CHK-112 — Global overturning and wall share

**Scope:** Building base cut, direction and load state. **Golden example:** `GE-CHK-112` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 4.3.4.5; 4.3.4.6; 4.3.4.7; 4.3.4.8; equations 4.2. Selected structural system and same-cut wall/frame overturning distribution; retain each applicable clause branch.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `same_cut_contributions` | Frame, wall and pier force states / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `reference_coordinates` | Common cut plane and moment reference / m | Transform forces and transport moments before summation. Source: Physical geometry. |
| `physical_ownership` | Nonduplicated frame/wall/pier ownership / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical member ledger. |
| `system_profile` | Applicable wall-share clause branch / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved profile. |

**Engineering prerequisites:** `SRC-003`, `SRC-004`, `SRC-005`, `CHK-140`, `CHK-146`.

#### Preserved implementation recipe

1. Transform all forces to a common direction and moments to one reference point.
2. Deduplicate wall and frame contributions by physical ownership.
3. Calculate overturning moment and applicable wall share under same-cut and compatible-demand semantics.

**Output:** Overturning balance, wall contribution ratio and contributing-member ledger.

**Acceptance:** Same-cut frame/pier contributions reconcile without duplicate physical members.

**Expected instance key:** `base_cut_id`, `direction`, `case_id`, `physical_contributor_id`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

Related source/catalog functions are retained without being counted as calculation owners:

- `src/tbdy_next/analysis_numerics.py::_base_reactions` — Observed base-reaction source arithmetic only.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-015`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No full same-cut frame/wall overturning partition owner was found. Base-reaction observation alone is not this physical calculation.

**Negative scenario to preserve:** Count one wall through both shell and pier representations; the sum must not be qualified.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-112` preserves example provenance and coverage.

### CHK-113 — Global second-order indicator

**Scope:** Story, direction, earthquake case and global method. **Golden example:** `GE-CHK-113` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 4.9.2.1; 4.9.2.2; equations 4.35, 4.36. Same-case story drift, shear and cumulative supported weight; below-limit screening does not certify native P-delta application.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `mean_relative_displacement` | Same-state story mean displacement / m | Nonnegative physical magnitude; retain the declared unit. Source: CHK-010. |
| `individual_story_weights` | Individual weights in physical story order / kN | Sum above the evaluated story once; do not supply already cumulative weights as individual. Source: CHK-101. |
| `story_shear` | Compatible directional story shear / kN | Nonnegative physical magnitude; retain the declared unit. Source: Same-case force owner. |
| `story_height` | Physical story height / m | Nonnegative physical magnitude; retain the declared unit. Source: Geometry ledger. |
| `second_order_coefficients` | R,D,Ch / 1 | Applicable system/direction and global method. Source: Approved profile. |

**Engineering prerequisites:** `CHK-010`, `CHK-101`, `SRC-005`.

#### Preserved implementation recipe

1. Match drift, shear and weight to the same case, direction and scaling basis.
2. Calculate thetaII=DeltaMean*sum(w)/(Vi*hi) and the applicable limit.
3. Pass the global second-order method decision as a distinct feature to the demand owner.

**Output:** Global second-order indicator and method decision.

**Acceptance:** Compatible drift, story shear and cumulative weight reproduce an independent second-order comparison.

**Expected instance key:** `physical_story_id`, `direction`, `case_id`, `second_order_method_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/story_pdelta.py::review_story_pdelta` | Directional thetaII and below-limit candidate using explicit individual story weights. |
| `src/tbdy_next/story_second_order.py::bind_story_second_order` | Bind same-source story evidence. |

**Registered stages:** `second-order`. **Existing GAP references:** `GAP-009`, `GAP-018`.

**Inspected implementation:** The conditional thetaII screening owner exists.

**Remaining work:** Approve cumulative weight, physical story/cut population, compatible drift/shear scaling and above-limit treatment. Actual P-delta application is not certified by theta alone.

**Negative scenario to preserve:** Substitute one-story weight for cumulative weight or mix drift scales; the result must remain unaccepted.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-113` preserves example provenance and coverage.

### CHK-114 — Base load transfer

**Scope:** Superstructure base cut and load state. **Golden example:** `GE-CHK-114` (DERIVED_BENCHMARK).

#### Specification and applicability

- **YENI engineering source and integration contract, Existing 73-card recipe, 2026-11-18.** Engineering integration contract. Superstructure-to-foundation transfer on a declared physical cut and common reference point; same model generation and load state.
- **Turkish Building Earthquake Code (TBDY), 2018.** 4.7.2.6; equations 4.25. Applicable equivalent-lateral-load overturning relation is separate from the generic force-transfer contract.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `base_reactions` | Same-state base/joint/pier/frame reactions / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `reference_geometry` | Base plane and common moment reference / m | Global force orientation and moment transport use the same right-handed frame. Source: Physical base geometry. |
| `reaction_ownership` | Exclusive contributor ownership / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical member ledger. |

**Engineering prerequisites:** `SRC-003`, `SRC-004`, `SRC-005`.

#### Preserved implementation recipe

1. Identify the physical base cut and the owner of every reaction contribution.
2. Transform forces to one coordinate system and moments to one reference point.
3. Record total force/moment equilibrium and the load states delivered to the foundation.

**Output:** Base-load transfer ledger and equilibrium residuals.

**Acceptance:** A common reference point and compatible source generation support force and moment balance.

**Expected instance key:** `base_cut_id`, `case_id`, `step_identity`, `physical_reaction_owner`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

Related source/catalog functions are retained without being counted as calculation owners:

- `src/tbdy_next/analysis_numerics.py::_base_reactions` — Base-reaction source observations only.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete foundation load-transfer ledger/calculation was found; define the interface binding before consuming reactions.

**Negative scenario to preserve:** Sum moments referred to different points; missing transformations must appear as unresolved lineage or equilibrium residuals.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-114` preserves example provenance and coverage.

### CHK-115 — TS 500 minimum eccentricity

**Scope:** Column compression demand and local bending axis. **Golden example:** `GE-CHK-115` (SOURCE_RECALC).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 6.3.10; equations 6.16. Compression demand and actual bending-plane dimension; apply the minimum eccentricity in the declared second-order sequence.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `Nd` | Compression demand / kN | Compression positive; tension must not be converted to compression by abs. Source: Signed source conversion. |
| `section_dimensions` | Physical section dimensions / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `M2_M3` | Signed local moments / kN*m | M2 is about local 2 and M3 about local 3; preserve sign except the declared zero-moment choice. Source: Same physical force state. |
| `local_axis_angle` | Captured section/frame rotation / degree | Signed orientation under the explicitly declared rotation convention. Source: Native axis assignment. |

**Engineering prerequisites:** `SRC-003`, `SRC-005`, `CHK-003`.

#### Preserved implementation recipe

1. Convert native dimensions into local physical dimensions exactly once.
2. Calculate emin=15+0.03h mm and the minimum compression moment for each bending axis.
3. Apply the applicable sign and analysis-order policy and bind the moment floor to the demand revision.

**Output:** Minimum-eccentricity demand and intermediate quantities for both axes.

**Acceptance:** Correct bending-plane dimensions and sign policy produce the two-axis design-moment floor.

**Expected instance key:** `column_unique_id`, `physical_cut_key`, `combination_id`, `local_bending_axis`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/ts500_column.py::minimum_eccentricity_mm` | Exact Decimal eccentricity formula. |
| `src/tbdy_next/column_engine/ts500_column.py::apply_minimum_eccentricity` | Signed local moment floors and explicit rotated projection. |

**Registered stages:** `column-pmm`, `column-r08-local`. **Existing GAP references:** `GAP-009`, `GAP-010`.

**Inspected implementation:** Both-axis minimum eccentricity is implemented with typed dimension conversion.

**Remaining work:** Qualify physical axes, native force signs and the order of application with local/global second-order effects.

**Negative scenario to preserve:** Swap M2/M3 dimensions for an unequal rectangle; an independent example must expose the incorrect floor.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-115` preserves example provenance and coverage.

### CHK-116 — Free length and slenderness

**Scope:** Column physical end faces and direction. **Golden example:** `GE-CHK-116` (DERIVED_BENCHMARK).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 7.6.2.3. Physical free length and section radius i=sqrt(I/A); the optional 0.3h approximation is a separately identified method.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `physical_end_faces` | Supporting faces and offset geometry / m | I/J orientation and active span are physical; force-row extrema do not define free length. Source: Geometry ledger. |
| `section_dimensions` | Physical section dimensions / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `section_properties` | A,I2,I3 / A: mm^2; I: mm^4 | Inertia refers to the same local axes as bending moments. Source: Section geometry. |

**Engineering prerequisites:** `SRC-003`, `CHK-003`.

#### Preserved implementation recipe

1. Read actual supporting faces and the active column segment from the geometry ledger.
2. Measure free length independently of force-output station locations.
3. Calculate i=sqrt(I/A) and the relevant slenderness measures in each direction.

**Output:** Free-length/slenderness feature and face/geometry evidence.

**Acceptance:** Physical topology establishes clear length and the correct section inertia establishes slenderness.

**Expected instance key:** `column_unique_id`, `physical_end_faces`, `local_bending_axis`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/ts500_column.py::rectangle_properties` | Section radii of gyration. |
| `src/tbdy_next/column_engine/ts500_column.py::evaluate_slenderness` | Slenderness for supplied accepted ln and k. |
| `src/tbdy_next/engineering/column_r10_live.py::_column_clear_length_m` | Observed frame length minus captured end offsets. |

**Registered stages:** `column-r08-local`, `column-r10`. **Existing GAP references:** `GAP-006`, `GAP-009`.

**Inspected implementation:** Radius/slenderness arithmetic and an offset-based length observation exist.

**Remaining work:** Approve actual supporting faces and TS 500 free length; the offset-derived span is not automatically a normative unsupported length.

**Negative scenario to preserve:** Use the last force station as free length in an offset member; this shortcut must not qualify the length.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-116` preserves example provenance and coverage.

### CHK-117 — Effective length coefficients

**Scope:** Column axis and restraint conditions at both ends. **Golden example:** `GE-CHK-117` (SOURCE_RECALC).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 7.6.2.2. Effective-length method with evidenced restraint stiffness and sway classification; a supplied k is not a derivation of k.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `joint_stiffnesses` | Incident member EI/L at both ends / N*mm | Each member stiffness uses the qualified cracked-stiffness and local-axis projection. Source: Physical joint topology and material/section properties. |
| `restraints_and_sway` | End restraints and sway classification / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved stability model. |
| `free_length` | Accepted physical free length / mm | Nonnegative physical magnitude; retain the declared unit. Source: CHK-116. |
| `effective_length_method` | Method branch and revision / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved engineering method. |

**Engineering prerequisites:** `CHK-116`, `CHK-147`.

#### Preserved implementation recipe

1. Build complete upper and lower joint stiffness contributions for each axis.
2. Apply the accepted effective-length method and boundary-condition branch.
3. Retain k2/k3 and lk=k*ln with method and sway revisions.

**Output:** Effective-length feature and end-stiffness calculations.

**Acceptance:** Directional effective length, sway and neighboring stiffness are bound to the accepted method branch.

**Expected instance key:** `column_unique_id`, `local_bending_axis`, `upper_joint_id`, `lower_joint_id`, `stability_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

Related source/catalog functions are retained without being counted as calculation owners:

- `src/tbdy_next/column_engine/ts500_column.py::evaluate_slenderness` — Consumes supplied k; does not derive effective-length coefficients.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-009`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete automatic joint-stiffness-to-k method owner was found. Existing arithmetic consumes a supplied k without approving it.

**Negative scenario to preserve:** Replace missing beam stiffness with zero or silently assume k=1; the effective length must remain unqualified.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-117` preserves example provenance and coverage.

### CHK-118 — Global P-delta ownership

**Scope:** Analysis generation, global method and design-demand revision. **Golden example:** `GE-CHK-118` (CONTRACT_FIXTURE).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 7.6. Local second-order applicability and ownership must be consistent with the chosen analysis method.
- **Turkish Building Earthquake Code (TBDY), 2018.** 4.9.2. Global second-order method and applied demand transformation must be explicit and free of duplicate amplification.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `analysis_order_settings` | Native P-delta, initial state and local geometry settings / not_applicable | Identity and revision are exact; no numeric coercion. Source: Same-generation case source. |
| `method_ownership` | Global and local effects already included versus still required / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved method matrix. |
| `convergence_and_generation` | Analysis completion and force freshness / not_applicable | Identity and revision are exact; no numeric coercion. Source: SRC-004. |
| `local_slenderness` | Applicable slenderness branches / not_applicable | Identity and revision are exact; no numeric coercion. Source: CHK-116 and CHK-117. |

**Engineering prerequisites:** `SRC-004`, `CHK-113`, `CHK-116`, `CHK-117`.

#### Preserved implementation recipe

1. Record which global/local effects are included in analysis using a method/component coverage matrix.
2. Compare required post-analysis effects against the evidenced analysis coverage.
3. Apply each amplification through exactly one existing owner and one demand revision.

**Output:** Second-order ownership decision and demand-application trace.

**Acceptance:** Analysis-included and postprocessed second-order effects have distinct, evidenced ownership.

**Expected instance key:** `analysis_case_id`, `member_id`, `local_bending_axis`, `second_order_method_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

Related source/catalog functions are retained without being counted as calculation owners:

- `src/tbdy_next/engineering/analysis_setup.py::audit_model_analysis_setup` — P-delta/generation prerequisite audit.
- `src/tbdy_next/engineering/story_pdelta.py::review_story_pdelta` — Theta screening; expressly not actual nonlinear P-delta analysis.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-009`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete accepted analysis-component ownership/application matrix was found. Generation and global/local effect proofs remain necessary.

**Negative scenario to preserve:** Apply the same global factor again to demand already containing that effect; double counting must be rejected.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-118` preserves example provenance and coverage.

### CHK-119 — Local second-order moment magnification

**Scope:** Column axis, case and signed end-moment pair. **Golden example:** `GE-CHK-119` (SOURCE_RECALC).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 7.6; equations 7.19, 7.24, 7.27, 7.28, 7.29. Applicable member/sway branch; multiplication of local and system factors is permitted only in the qualified Eq. 7.29 branch.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `Nd` | Compression demand / kN | Compression positive; retain force state with moments. Source: Same physical demand state. |
| `end_moments` | Signed same-axis end moments / kN*m | Cm requires compatible end signs and the stated curvature convention. Source: Signed demand state. |
| `section_stiffness` | Ec,Ic,Es,Is / E: MPa; I: mm^4 | Use the declared cracked/time-dependent branch. Source: Selected section and cage. |
| `Rm` | Sustained-load or creep ratio / 1 | Nonnegative physical magnitude; retain the declared unit. Source: Approved load-duration evidence. |
| `effective_length` | Accepted k*ln / mm | Nonnegative physical magnitude; retain the declared unit. Source: CHK-117. |
| `amplification_branch` | Local/system and Eq. 7.29 ownership / not_applicable | Identity and revision are exact; no numeric coercion. Source: CHK-118. |

**Engineering prerequisites:** `CHK-115`, `CHK-116`, `CHK-117`, `CHK-118`.

#### Preserved implementation recipe

1. Calculate Nk=pi^2*EIeff/lk^2 from directional effective length and stiffness.
2. Determine end-moment ratio, Cm and magnification parameters under the correct sway/creep branch.
3. Bind M2/M3 magnifications to the same demand state and retain domain and residual checks.

**Output:** Local second-order demand with axis-specific calculation trace.

**Acceptance:** EI, Nk, creep, k and signed end-moment ratio reproduce the independent magnification under the selected branch.

**Expected instance key:** `column_unique_id`, `physical_cut_key`, `combination_id`, `local_bending_axis`, `second_order_method_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/ts500_column.py::effective_stiffness_nmm2` | Declared TS 500 EI branches. |
| `src/tbdy_next/column_engine/ts500_column.py::euler_load_kn` | Euler Nk from supplied EI/lk. |
| `src/tbdy_next/column_engine/ts500_column.py::moment_magnification_factors` | Conditional local/story magnification coefficients. |
| `src/tbdy_next/engineering/column_r08_local_live.py::project_column_r08_local_live` | Bind same-run local second-order reference results. |

**Registered stages:** `column-r08-local`. **Existing GAP references:** `GAP-009`, `GAP-010`.

**Inspected implementation:** EI, Nk and magnification coefficient arithmetic and R08 projection exist.

**Remaining work:** Approve k, sway, free length, creep, signed end ratios, Eq.7.29 applicability and actual demand consumption without duplication.

**Negative scenario to preserve:** Lose an end-moment sign or enter an unstable Nd domain; do not report a valid finite magnification.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-119` preserves example provenance and coverage.

### CHK-120 — Final biaxial PMM assessment

**Scope:** Selected column cage and all design cuts. **Golden example:** `GE-CHK-120` (DERIVED_BENCHMARK).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 6.2.5; 7.1; Table 7.1. Declared concrete stress block, steel law, strain limits, axis/sign convention and same selected cage; unsigned spectrum bounds are not concurrent vectors.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `section_dimensions` | Physical section dimensions / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `selected_cage` | Actual or explicitly selected reinforcing cage / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `design_demands` | Demands after qualified eccentricity and second-order treatment / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `constitutive_method` | Stress block, strain limits, axial cap and capacity interpolation / not_applicable | Identity and revision are exact; no numeric coercion. Source: Existing section owner. |
| `spectral_bound_semantics` | Envelope scope and mathematical qualification if used / not_applicable | Identity and revision are exact; no numeric coercion. Source: Qualified spectral demand owner. |

**Engineering prerequisites:** `CHK-007`, `CHK-009`, `CHK-115`, `CHK-119`.

#### Preserved implementation recipe

1. Bind every required member/case/cut to the same selected-cage revision; use separate signed-state and spectral-interval method records.
2. Integrate concrete and steel contributions through the existing strain-compatibility capacity owner.
3. Record utilization and numerical quality for every state, spectral transformation/bounding evidence, the governing state and the full population.

**Output:** Final PMM comparisons over all required design states.

**Acceptance:** Full case/cut coverage uses the same cage and correct demand order; spectral-box acceptance additionally satisfies its capacity-set and transformation-bounding contract.

**Expected instance key:** `column_unique_id`, `physical_cut_key`, `combination_id`, `step_identity`, `cage_revision`, `design_demand_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/section_capacity.py::solver` | Canonical strain-compatible section-capacity solver. |
| `src/tbdy_next/engineering/column_r08_local_live.py::_evaluate_spectral_bounding_corners` | Conditional spectral-box corner evaluation. |
| `src/tbdy_next/engineering/column_r14_closure.py::project_column_r14_and_r15_closure` | Project recorded design closure prerequisites. |

**Registered stages:** `column-pmm`, `column-r08-local`. **Existing GAP references:** `GAP-006`, `GAP-009`, `GAP-010`, `GAP-018`.

**Inspected implementation:** Signed PMM and explicitly conditional spectral-corner calculations exist.

**Remaining work:** Complete physical cut/load/cage scope; prove spectral containment, convexity and nonlinear transformation bounds before a box can establish acceptance.

**Integration note:** The R14 function listed here is a closure projection, not an alternative section-capacity formula owner. An eight-corner scalar box result remains a bound candidate; it cannot establish simultaneity, complete load scope or a nonlinear transformation bound without separate proof.

**Negative scenario to preserve:** Delete one critical cut or use capacity from a different cage; low remaining utilization must not close the check.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-120` preserves example provenance and coverage.

### CHK-121 — Column longitudinal detailing

**Scope:** Column cage, individual bars and splice regions. **Golden example:** `GE-CHK-121` (DERIVED_BENCHMARK).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.3.2.1; 7.3.3. Column longitudinal ratio, arrangement, lap regions and supported detailing branch.
- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 9.5.1; 9.5.2. Clear bar spacing and actual placement with cover, tie diameter and aggregate size.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `section_dimensions` | Physical section dimensions / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `selected_cage` | Actual or explicitly selected reinforcing cage / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `aggregate_size` | Maximum aggregate dimension / mm | Nonnegative physical magnitude; retain the declared unit. Source: Material/project specification. |
| `region_and_splice` | Physical longitudinal region and splice branch / not_applicable | Identity and revision are exact; no numeric coercion. Source: Detailing source. |
| `policy_area_floor` | Additional project floor, if any / mm^2 | Nonnegative physical magnitude; retain the declared unit. Source: Explicit project policy. |

**Engineering prerequisites:** `CHK-009`, `CHK-120`.

#### Preserved implementation recipe

1. Construct the physical bar-layout geometry.
2. Evaluate cover, clear spacing and lateral support against bar pairs and section boundaries.
3. Apply anchorage, splice and regional detailing rules at their physical locations.

**Output:** Longitudinal detailing result and feasible cage geometry.

**Acceptance:** Bar centers, cover, clear distances, anchorage and splices satisfy their applicable rule cards.

**Expected instance key:** `column_unique_id`, `longitudinal_region`, `cage_revision`, `bar_or_layer_id`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/rebar_selection.py::select_column_rebar` | Supported rectangular candidate area/spacing selection. |

**Registered stages:** `column-r10`. **Existing GAP references:** `GAP-011`.

**Inspected implementation:** Finite candidate selection checks supported bar area and spacing.

**Remaining work:** Complete actual bar coordinates, aggregate-dependent spacing, splice zones, anchorage and approved cage identity.

**Negative scenario to preserve:** Supply adequate steel area with overlapping bars; area alone must not establish detailing compliance.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-121` preserves example provenance and coverage.

### CHK-122 — Column confinement regions

**Scope:** Column end region and physical support face. **Golden example:** `GE-CHK-122` (DERIVED_BENCHMARK).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.3.4.1. Normal-story column-end confinement regions; special foundation, discontinuity or splice branches require separate scope.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `section_dimensions` | Physical section dimensions / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `clear_length` | Accepted physical clear length / mm | Nonnegative physical magnitude; retain the declared unit. Source: CHK-116. |
| `region_topology` | End/support/foundation/splice classification / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical topology. |

**Engineering prerequisites:** `CHK-116`, `CHK-147`.

#### Preserved implementation recipe

1. Locate the physical starting face of confinement at each end.
2. Derive confinement length under the applicable rule branch.
3. Record upper/lower confinement and middle-region intervals with overlap and coverage checks.

**Output:** Column confinement regions with geometry references.

**Acceptance:** Correct clear length and section geometry determine the regional confinement requirement.

**Expected instance key:** `column_unique_id`, `physical_end`, `region_type`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

Related source/catalog functions are retained without being counted as calculation owners:

- `src/tbdy_next/engineering/rebar_selection.py::_evaluate_column_transverse_choice` — Regional tie choice and confinement area, not full end-region length geometry.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-011`, `GAP-014`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete physical-face-based column confinement-region length owner was found. Regional tie spacing/reference calculations do not establish the required column end-zone length.

**Negative scenario to preserve:** Shorten confinement using an output station or unknown support face; regional coverage must remain unresolved.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-122` preserves example provenance and coverage.

### CHK-123 — Tie and crosstie topology

**Scope:** Transverse leg, longitudinal bar and detailing region. **Golden example:** `GE-CHK-123` (DERIVED_BENCHMARK).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.3.4.1. Physical laterally supported bar topology and maximum horizontal leg spacing; vertical pitch and tie diameter remain separate checks.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `section_dimensions` | Physical section dimensions / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `transverse_and_longitudinal_cage` | Closed ties, crossties, supported bars, cover and hooks / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `leg_coordinates` | Actual effective tie/crosstie line coordinates / mm | Compare gaps in each physical section direction; a declared leg count is insufficient. Source: Cage geometry. |

**Engineering prerequisites:** `CHK-121`, `CHK-122`.

#### Preserved implementation recipe

1. Model closed ties and crosstie legs using actual coordinates.
2. Calculate lateral support of every longitudinal bar and horizontal leg spacing.
3. Assess vertical pitch and regional diameter/spacing rules independently.

**Output:** Transverse topology result, leg list and regional detailing results.

**Acceptance:** Actual leg geometry, unsupported bars and horizontal/vertical distances are independently assessed.

**Expected instance key:** `column_unique_id`, `transverse_region`, `cage_revision`, `section_direction`, `supported_bar_id`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/column_gates.py::evaluate_transverse_leg_topology` | Supported rectangular tie/crosstie leg and spacing checks. |
| `src/tbdy_next/engineering/rebar_selection.py::_min_crosstie_legs_for_face` | Required tied-leg count on a declared face. |

**Registered stages:** `column-r10`. **Existing GAP references:** `GAP-011`, `GAP-014`.

**Inspected implementation:** Supported rectangular leg-spacing and pitch arithmetic exists.

**Remaining work:** Qualify actual crosstie polygons, supported longitudinal bars, hook orientation and three-dimensional fit.

**Negative scenario to preserve:** Remove an intermediate crosstie while retaining nominal steel area; topology failure must remain visible.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-123` preserves example provenance and coverage.

### CHK-124 — Required transverse reinforcement area

**Scope:** Column direction, transverse region and axial state. **Golden example:** `GE-CHK-124` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.3.4.1; equations 7.1. Applicable confinement region and axial branch; the two-thirds reduction requires explicit evidence of eligibility.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `section_dimensions` | Physical section dimensions / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `selected_cage` | Actual or explicitly selected reinforcing cage / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `Ac` | Gross section area / mm^2 | Nonnegative physical magnitude; retain the declared unit. Source: Section geometry. |
| `Ack` | Confined core area under declared core definition / mm^2 | Nonnegative physical magnitude; retain the declared unit. Source: Tie centre/core geometry. |
| `Nd` | Applicable axial demand / kN | Compression positive with explicit seismic role. Source: Qualified axial population. |
| `tie_pitch` | Region-specific tie spacing / mm | Nonnegative physical magnitude; retain the declared unit. Source: Selected cage. |

**Engineering prerequisites:** `CHK-004`, `CHK-121`, `CHK-122`, `CHK-123`.

#### Preserved implementation recipe

1. Derive confined-core dimensions using the rule-specific measurement convention.
2. Calculate required Ash for every direction/region under the applicable axial-load branch.
3. Sum provided areas only from legs effective in that direction and compare required/provided area.

**Output:** Required/provided transverse areas and regional utilization.

**Acceptance:** Core dimensions, effective leg directions and rule branch support the area comparison.

**Expected instance key:** `column_unique_id`, `confinement_region`, `section_direction`, `axial_branch`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/transverse_kernel.py::confinement_reference` | Both Eq.7.1 area branches with explicit inputs. |

**Registered stages:** `column-r10`. **Existing GAP references:** `GAP-011`, `GAP-014`.

**Inspected implementation:** Directional confinement area and required/provided comparisons exist as conditional branches.

**Remaining work:** Select the applicable axial branch from the full demand population and establish actual effective leg/core geometry.

**Negative scenario to preserve:** Count legs from the wrong direction in Ash; false area sufficiency must be rejected.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-124` preserves example provenance and coverage.

### CHK-125 — Strong column weak beam

**Scope:** Joint, direction, earthquake sign and column axial-demand state. **Golden example:** `GE-CHK-125` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.3.5.1; equations 7.3. Applicable joint, principal axis, earthquake sign and column axial-demand state; selected beam/column reinforcement is required.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `joint_topology` | Column and beam ends, axes and positive absences / not_applicable | Identity and revision are exact; no numeric coercion. Source: CHK-147. |
| `column_cages` | Same-revision upper/lower column cages / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `beam_cages` | Same-revision incident beam face cages / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `axial_state` | Column axial demand compatible with the SCWB case/sign / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `signed_end_capacities` | Column and beam capacities by axis, face and earthquake sign / kN*m | Capacities are positive magnitudes tagged with physical sign/face and N; do not sum incompatible sign states. Source: Existing section and beam capacity owners. |

**Engineering prerequisites:** `SRC-005`, `CHK-120`, `CHK-134`, `CHK-147`.

#### Preserved implementation recipe

1. Select capacities at the correct joint faces and bending signs.
2. Evaluate column capacities over the required Nd population and beam capacities at the selected-bar revision.
3. Record the applicable SCWB inequality and exceptions for every direction/sign.

**Output:** Joint SCWB result and capacity-contribution table.

**Acceptance:** The complete incident roster and compatible column/beam capacity revisions support each SCWB decision.

**Expected instance key:** `joint_id`, `frame_axis`, `earthquake_sign`, `axial_state_id`, `column_cage_revision`, `beam_cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/scwb_kernel.py::compute_scwb_joint_result` | Same-context joint capacity aggregation and inequality. |
| `src/tbdy_next/column_engine/scwb_kernel.py::column_axis_capacity` | Column principal-axis capacity at supplied N. |
| `src/tbdy_next/engineering/column_r10_live.py::_evaluate_scwb_at_joint_ends` | Physical joint/end projection and selected capacities. |

**Registered stages:** `column-r10`. **Existing GAP references:** `GAP-011`, `GAP-012`, `GAP-013`, `GAP-018`.

**Inspected implementation:** Same-context capacity aggregation and explicit fixed-N principal-axis calculations exist.

**Remaining work:** Qualify governing axial demand, all incident selected cages, both direction/signs and applicable exceptions. Spectral component maxima do not supply concurrent Nd.

**Negative scenario to preserve:** Replace a missing neighboring column cage with template capacity; the joint cannot close on that substitution.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-125` preserves example provenance and coverage.

### CHK-126 — Column capacity shear demand

**Scope:** Both column ends, direction, sign and cage. **Golden example:** `GE-CHK-126` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.3.7; equations 7.5. Applicable column end mechanism, beam distribution and alternatives; preserve the raw design-demand floor and physical free length.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `end_moment_mechanism` | Compatible plastic capacities at both ends / kN*m | Retain joint role, local axis, sign and distribution branch. Source: SCWB and selected cage capacities. |
| `clear_length` | Accepted free length / m | Nonnegative physical magnitude; retain the declared unit. Source: CHK-116. |
| `raw_design_state` | Physical signed force state / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `alternative_eligibility` | D alternative, beamless ends and raw-demand floor provenance / not_applicable | Identity and revision are exact; no numeric coercion. Source: Method branch and force lineage. |

**Engineering prerequisites:** `CHK-116`, `CHK-125`, `CHK-134`.

#### Preserved implementation recipe

1. Produce applicable upper/lower end capacities under the same cage and axial-demand policy.
2. Choose framed and beamless end conditions from physical topology.
3. Compare Ve and applicable alternatives/lower bounds in both directions and earthquake signs.

**Output:** Column capacity-shear demand and end-specific moment lineage.

**Acceptance:** Every expected state uses applicable end capacities, clear length and demand policy.

**Expected instance key:** `column_unique_id`, `local_shear_axis`, `earthquake_sign`, `end_mechanism`, `design_demand_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/column_r10_live.py::_compute_capacity_shear_axes` | Two-end capacity shear including beamless ends and revised Vd floor. |

**Registered stages:** `column-r10`. **Existing GAP references:** `GAP-006`, `GAP-013`, `GAP-014`.

**Inspected implementation:** Unreduced end-capacity branches and beamless-column demand evaluation exist.

**Remaining work:** Complete physical clear length, analysis-moment distribution where selected, governing Nd, D alternative and both-sign coverage.

**Negative scenario to preserve:** Skip a beamless column or reuse one end capacity at both ends; coverage and numerical checks must detect the error.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-126` preserves example provenance and coverage.

### CHK-127 — Column shear resistance

**Scope:** Column cut, region, direction and design state. **Golden example:** `GE-CHK-127` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.3.7.2; 7.3.7.3; 7.3.7.4; 7.3.7.5. Column shear and applicable special-region concrete-contribution rule.
- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 8.1.4; 8.1.5. Concrete and transverse-steel shear contributions with the same selected cage and applicable material branch.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `Ve` | Governing capacity-shear demand / kN | Nonnegative physical magnitude; retain the declared unit. Source: CHK-126. |
| `section_dimensions` | Physical section dimensions / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `selected_transverse_cage` | Actual effective legs and pitch / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `concrete_contribution_branch` | Special-region Vc=0 or qualified contribution / not_applicable | Identity and revision are exact; no numeric coercion. Source: Axial/seismic/region evidence. |

**Engineering prerequisites:** `CHK-123`, `CHK-124`, `CHK-126`.

#### Preserved implementation recipe

1. Calculate concrete and transverse-steel contributions under the correct axis/region branch.
2. Compare Ve with Vr and any brittle upper limit separately.
3. Record mechanical capacity and tie/crosstie detailing decisions together without suppressing either.

**Output:** Column shear result with distinct capacity and detailing decisions.

**Acceptance:** Ve/Vr, special-region conditions and transverse-detail requirements are all evaluated.

**Expected instance key:** `column_unique_id`, `physical_region`, `local_shear_axis`, `cage_revision`, `demand_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/transverse_kernel.py::shear_reference` | Conditional concrete/steel shear resistance. |
| `src/tbdy_next/column_engine/transverse_kernel.py::zero_concrete_gate` | Seismic-share and low-axial concrete-neglect condition. |
| `src/tbdy_next/engineering/column_r10_live.py::_finish_column_shear_and_confinement` | Bind selected cage and source demand references. |

**Registered stages:** `column-r10`. **Existing GAP references:** `GAP-011`, `GAP-014`.

**Inspected implementation:** Shear resistance and explicit concrete-neglect scenarios exist.

**Remaining work:** Bind final Ve and accepted applicability; validate brittle bounds and physical tie details independently of mechanical capacity.

**Negative scenario to preserve:** Supply adequate mechanical capacity with inadequate ties; the capacity ratio must not hide detailing failure.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-127` preserves example provenance and coverage.

### CHK-128 — Beam column joint panel shear

**Scope:** Joint panel, direction, sign and physical face. **Golden example:** `GE-CHK-128` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.5.1; 7.5.2; equations 7.11. Applicable joint enclosure, geometry and moment/force transfer; centered unconfined limit is a supported numerical subset only.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `joint_geometry` | Core dimensions, beam widths, offsets and enclosure / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical joint geometry. |
| `joint_demand` | Compatible transferred beam/column end forces / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `face_reinforcement_forces` | Applicable steel forces at joint faces / kN | Retain face, tension direction, cage and material strength. Source: Selected beam cages and signed capacities. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |

**Engineering prerequisites:** `CHK-125`, `CHK-134`, `CHK-147`, `CHK-148`.

#### Preserved implementation recipe

1. Bind all incident members to compatible demand and capacity revisions.
2. Derive Vj from panel force equilibrium and resistance from effective panel geometry.
3. Evaluate panel shear, transverse reinforcement and anchorage as distinct sub-results.

**Output:** Joint-panel result and force-equilibrium calculation.

**Acceptance:** Panel demand, effective geometry, confinement and anchorage use the same complete joint roster.

**Expected instance key:** `joint_id`, `frame_axis`, `earthquake_sign`, `joint_geometry_revision`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/joint_kernel.py::centered_joint_limit` | Centered orthogonal geometric joint limit. |
| `src/tbdy_next/engineering/column_r10_live.py::_attach_r13_joint_shear_and_transverse` | Joint equilibrium and transverse projection. |

**Registered stages:** `column-r10`. **Existing GAP references:** `GAP-006`, `GAP-011`, `GAP-012`, `GAP-014`.

**Inspected implementation:** A centered-joint limit and same-run panel/shear projection exist.

**Remaining work:** Approve full end/face geometry, off-center branches, selected bars, post-alpha joint equilibrium and anchorage.

**Negative scenario to preserve:** Treat absent upper-column force as zero; without positive roof-topology evidence the check cannot close.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-128` preserves example provenance and coverage.

### CHK-129 — Converged column design iteration

**Scope:** Design scenario and dependent member group. **Golden example:** `GE-CHK-129` (CONTRACT_FIXTURE).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.3.6. Applicable story/direction shear participation and allowed alpha correction; revision, reanalysis and convergence are integration requirements.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `story_shear_partition` | Same-cut signed Vi and eligible Vis / kN | All physical columns share one case/direction and qualified cut; independent spectrum extrema are not signed addends. Source: Complete physical force and SCWB ledgers. |
| `prior_design_revision` | Member demand and cage revision consumed by SCWB / not_applicable | Identity and revision are exact; no numeric coercion. Source: Immutable design results. |
| `iteration_policy` | Eligible alpha branch, bounded iteration and convergence tolerance / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved project/method policy. |

**Engineering prerequisites:** `CHK-125`, `CHK-126`, `CHK-127`, `CHK-128`, `CHK-146`.

#### Preserved implementation recipe

1. Rank candidates by a recorded objective and deterministic tie-break rule.
2. At each iteration derive absolute factors from immutable base demand and reevaluate all changed demand/cage dependents at one revision.
3. Distinguish fixed point, exhausted candidate family, search limit and repeated-state cycle termination.

**Output:** Design iteration result, evaluated demand/cage revision per step, search scope and final candidate.

**Acceptance:** The bounded loop tracks demand/cage/alpha revisions; stable results have all consumers on the same evaluated revision. Optimality is limited to the declared candidate family.

**Expected instance key:** `physical_story_id`, `direction`, `qualified_case_id`, `design_iteration`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/alpha_iteration.py::run_bounded_feedback` | Bounded feedback termination mechanics. |
| `src/tbdy_next/engineering/alpha_iteration.py::run_alpha_design_iteration` | Existing owner-based signed demand/cage feedback. |
| `src/tbdy_next/column_engine/story_alpha.py::evaluate_story_alpha_reference` | Supplied story shear ratio. |
| `src/tbdy_next/column_engine/story_alpha.py::alpha_feedback_factor` | Inclusive 0.70..1.00 feedback factor. |

**Registered stages:** `alpha-feedback`, `design-revisions`. **Existing GAP references:** `GAP-013`, `GAP-016`, `GAP-018`.

**Inspected implementation:** Bounded signed-source feedback and deterministic demand/cage revisions exist.

**Remaining work:** Complete the independent modal-to-alpha example and qualified governing Nd/story partition; preserve all nonconvergence states and full downstream revision consistency.

**Integration note:** The existing signed alpha subset is narrower than the complete spectral chain. The recipe dependency on CHK-146 describes the intended full physical shear partition; it does not erase the existing qualified column-only subset.

**Negative scenario to preserve:** Compound alpha on already amplified demand or introduce cage cycling; false convergence must be prevented.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-129` preserves example provenance and coverage.

### CHK-130 — Beam physical geometry and applicability

**Scope:** Beam object, ends, section and structural role. **Golden example:** `GE-CHK-130` (DERIVED_BENCHMARK).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.4.1.1; 7.4.1.2. Frame beam role, physical supports/faces, section dimensions and clear span.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `beam_dimensions` | Actual beam width and depth / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `support_faces` | Physical I/J support faces and clear span / m | Beam end roles and the actual support geometry determine clear length. Source: Geometry ledger. |
| `beam_role` | Frame beam, coupling beam or other type / not_applicable | Identity and revision are exact; no numeric coercion. Source: Structural topology. |

**Engineering prerequisites:** `SRC-003`, `CHK-147`.

#### Preserved implementation recipe

1. Classify the member using its actual three-dimensional vector and structural role.
2. Bind the section and physical end faces through the native/local axis transformation.
3. Assess normative beam geometry and calculation-method applicability.

**Output:** Beam geometry and applicability result.

**Acceptance:** Independent geometry establishes axes, physical faces and eligibility for the beam method.

**Expected instance key:** `beam_unique_id`, `physical_end_faces`, `section_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/quick_checks.py::evaluate_geometry_capture` | Rectangular beam width/depth subconditions. |
| `src/tbdy_next/engineering/beam_r10_live.py::project_beam_r10_live` | Recorded beam ends, offsets and source design targets. |

**Registered stages:** `geometry`, `beam-r10-live`. **Existing GAP references:** `GAP-006`, `GAP-012`.

**Inspected implementation:** Supported rectangular beam geometry and end-source binding exist.

**Remaining work:** Qualify actual faces, axial applicability, inclined members and unsupported geometric families.

**Negative scenario to preserve:** Treat a sloping or differently classified axial member as an ordinary horizontal beam; unsupported scope must remain explicit.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-130` preserves example provenance and coverage.

### CHK-131 — Beam flexural design

**Scope:** Beam cut, face, moment sign and design state. **Golden example:** `GE-CHK-131` (DERIVED_BENCHMARK).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 6.2.5; 7.1. Supported beam flexural design model; the golden rectangular singly reinforced benchmark is not every flange/compression-steel branch.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `beam_section` | Actual web/flange geometry and effective depth / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `beam_flexural_demand` | Same-face signed beam demand / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `section_design_branch` | Singly/doubly reinforced or flange model and method revision / not_applicable | Identity and revision are exact; no numeric coercion. Source: Qualified beam design method. |

**Engineering prerequisites:** `SRC-005`, `CHK-130`.

#### Preserved implementation recipe

1. Select the design moment at the same physical cut and bending sign.
2. Solve required tension/compression reinforcement from equilibrium and constitutive relations.
3. Retain effective depth, strain/equilibrium residuals and required steel areas.

**Output:** Beam flexural-design result and required As values.

**Acceptance:** Correct demand, section and materials reproduce independent section calculations.

**Expected instance key:** `beam_unique_id`, `physical_face_or_station`, `bending_sign`, `combination_id`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

Related source/catalog functions are retained without being counted as calculation owners:

- `src/tbdy_next/engineering/beam_r10_live.py::_evaluate_beam_end` — Read/envelope source design area targets.
- `src/tbdy_next/column_engine/beam_capacity.py::signed_beam_capacity` — Evaluate supplied-cage N=0 capacity; not inverse required-As design.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-012`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete independent demand-to-required-As beam flexural design owner was found. The present beam path consumes ETABS required-area targets and evaluates selected-cage capacity.

**Negative scenario to preserve:** Use positive-moment reinforcement for negative-face demand; sign and layer identity must expose the error.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-131` preserves example provenance and coverage.

### CHK-132 — Selected beam reinforcement on both faces

**Scope:** Beam end or span cage and bar layer. **Golden example:** `GE-CHK-132` (DERIVED_BENCHMARK).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 9.5.1; 9.5.2. Actual beam bar placement, layers, cover and clear spacing.
- **Turkish Building Earthquake Code (TBDY), 2018.** 7.4.2. Beam longitudinal cage and seismic arrangement requirements.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `beam_section` | Physical beam section and available bar space / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `beam_candidate` | Candidate bar diameters, counts, layers and coordinates / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `aggregate_size` | Maximum aggregate dimension / mm | Nonnegative physical magnitude; retain the declared unit. Source: Project material specification. |
| `required_face_area` | Required upper/lower steel area / mm^2 | Each area retains face, station and same design revision. Source: Qualified beam flexural demand/design. |

**Engineering prerequisites:** `CHK-130`, `CHK-131`.

#### Preserved implementation recipe

1. Place bar-count/diameter/layer candidates inside the physical section.
2. Calculate clear spacing, effective depth and geometric feasibility for every candidate.
3. Select deterministically from supported layouts and retain bar coordinates.

**Output:** Selected beam cage with top and bottom layer geometry.

**Acceptance:** The selected candidate fits using real bar centers, cover and clear distances.

**Expected instance key:** `beam_unique_id`, `physical_region`, `tension_face`, `candidate_cage_revision`, `layer_id`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/beam_capacity.py::build_selected_beam_cage` | Actual supported top/bottom bar-layer placement. |
| `src/tbdy_next/engineering/rebar_selection.py::select_beam_station_rebar` | Finite supported bar-count/diameter selection from area targets. |

**Registered stages:** `beam-r10-live`. **Existing GAP references:** `GAP-011`, `GAP-012`.

**Inspected implementation:** Explicit multi-row selected cages and deterministic area-target selection exist.

**Remaining work:** Qualify complete end/span scope, aggregate/cover constraints, source-target lineage and actual constructibility.

**Negative scenario to preserve:** Invent an invisible second layer to fit excessive area; unsupported layout or infeasible geometry must remain explicit.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-132` preserves example provenance and coverage.

### CHK-133 — Beam reinforcement limits and continuity

**Scope:** Beam region and longitudinal reinforcement role. **Golden example:** `GE-CHK-133` (DERIVED_BENCHMARK).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.4.2. Beam upper/lower face and support/span reinforcement branches with the selected cage.
- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 7.3; equations 7.3, 7.4, 7.5. Applicable minimum/maximum flexural reinforcement and branch-specific limits.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `beam_section` | Width, depth and face-dependent effective depths / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `selected_beam_cage` | Actual or explicitly selected reinforcing cage / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `longitudinal_region` | Support/span and positive/negative face branch / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical beam region. |

**Engineering prerequisites:** `CHK-131`, `CHK-132`.

#### Preserved implementation recipe

1. Derive tension and compression reinforcement separately in every end/span region.
2. Compare normative ratio bounds and top/bottom relationships.
3. Track required continuous bars through actual geometry and reinforcement revision.

**Output:** Beam longitudinal-detailing result.

**Acceptance:** Applicable minimum, maximum and continuity conditions are evaluated separately by region.

**Expected instance key:** `beam_unique_id`, `physical_region`, `tension_face`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/beam_r10_live.py::_beam_longitudinal_rho_bounds` | Numerical beam ratio bounds. |
| `src/tbdy_next/engineering/rebar_selection.py::select_beam_station_rebar` | Selected top/bottom ratio and support-half conditions. |

**Registered stages:** `beam-r10-live`. **Existing GAP references:** `GAP-011`, `GAP-012`.

**Inspected implementation:** Supported regional ratio and face-relationship checks exist.

**Remaining work:** Track physical continuous bars through all regions and complete anchorage/splice requirements.

**Negative scenario to preserve:** Remove required continuous top or bottom bars while total As remains sufficient; detailing must fail.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-133` preserves example provenance and coverage.

### CHK-134 — Beam end signed moment capacities

**Scope:** Physical beam face, bending sign and cage revision. **Golden example:** `GE-CHK-134` (DERIVED_BENCHMARK).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 6.2.5; 7.1. Physical beam face, bending sign, material model and selected cage; the supported zero-axial section model must remain explicit.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `beam_section` | Supported web/flange geometry / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `selected_beam_cage` | Actual or explicitly selected reinforcing cage / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `face_sign_key` | Physical I/J face, local bending axis and sign / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical beam face ledger. |
| `axial_assumption` | Axial force for supported section model / kN | Signed; zero must be an evidenced supported assumption, not an ignored nonzero force. Source: Qualified method assumption. |

**Engineering prerequisites:** `CHK-132`, `CHK-133`.

#### Preserved implementation recipe

1. Read actual top/bottom bar positions at the physical I/J face.
2. Solve section equilibrium separately for positive and negative bending.
3. Pass Mr capacities to joint calculations with end, sign and cage-revision identity.

**Output:** Beam-face capacities with signed Mr values.

**Acceptance:** Both bending signs use the same selected physical layout and independent capacity comparison.

**Expected instance key:** `beam_unique_id`, `physical_end_face`, `bending_sign`, `cage_revision`, `section_method_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/beam_capacity.py::signed_beam_capacity` | Positive/negative N=0 selected-section capacities. |

**Registered stages:** `beam-r10-live`, `column-r10`. **Existing GAP references:** `GAP-011`, `GAP-012`.

**Inspected implementation:** Signed beam capacities are calculated by the existing section kernel for supported symmetric-width N=0 scenarios.

**Remaining work:** Qualify physical face/cage binding, axial applicability, slab participation and all required signs.

**Negative scenario to preserve:** Use I-end top reinforcement for J-end bottom capacity; the end/sign identity mismatch must be rejected.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-134` preserves example provenance and coverage.

### CHK-135 — Beam capacity shear demand

**Scope:** Both beam faces, earthquake sign and load state. **Golden example:** `GE-CHK-135` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.4.5.1; equations 7.9. Compatible gravity shear, correct plastic-end signs, actual clear span, eligible D alternative and raw Vd floor.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `plastic_end_moments` | Compatible end capacities / kN*m | Retain I/J face and earthquake sign; choose the correct pair for the mechanism. Source: CHK-134. |
| `gravity_end_shear` | Gravity-only shear at both ends / kN | Same physical face and compatible state; preserve signs before envelope. Source: Qualified combination decomposition. |
| `clear_span` | Actual distance between physical faces / m | Nonnegative physical magnitude; retain the declared unit. Source: CHK-130. |
| `raw_beam_state` | Physical signed force state / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `D_alternative` | Eligible D-amplified alternative and its source state / not_applicable | Identity and revision are exact; no numeric coercion. Source: Method and demand lineage. |

**Engineering prerequisites:** `SRC-005`, `CHK-130`, `CHK-134`.

#### Preserved implementation recipe

1. Bind the gravity contribution explicitly to its load-role source.
2. Calculate Ve candidates for each earthquake sign using end capacities and clear span.
3. Compare applicable alternatives and bounds and select governing design shear.

**Output:** Beam capacity-shear demand with contribution trace.

**Acceptance:** Correct gravity contribution, end moments and clear span determine capacity shear.

**Expected instance key:** `beam_unique_id`, `end_face`, `earthquake_sign`, `mechanism_branch`, `demand_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/beam_r10_live.py::_beam_gravity_shear_kn` | Bind gravity shear contribution. |
| `src/tbdy_next/engineering/beam_r10_live.py::_beam_shear_ve` | Derive capacity shear from both end capacities and clear span. |

**Registered stages:** `beam-r10-live`. **Existing GAP references:** `GAP-006`, `GAP-012`, `GAP-014`.

**Inspected implementation:** Gravity and end-capacity shear calculations exist.

**Remaining work:** Complete D-alternative, analysis-demand lower bound, face offsets, both-sign and post-alpha verification for the selected method.

**Negative scenario to preserve:** Use total seismic shear as Vdy without decomposition or bind the wrong end capacity; demand qualification must stop.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-135` preserves example provenance and coverage.

### CHK-136 — Beam transverse reinforcement

**Scope:** Beam end confinement and span regions. **Golden example:** `GE-CHK-136` (DERIVED_BENCHMARK).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 8.1.5. Applicable concrete/steel shear contributions and actual transverse steel.
- **Turkish Building Earthquake Code (TBDY), 2018.** 7.4.4; 7.4.5. Beam end/span regions, pitch, first tie, leg spacing and special concrete-contribution branch.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `Ve` | Qualified beam shear demand / kN | Nonnegative physical magnitude; retain the declared unit. Source: CHK-135. |
| `beam_section` | b,h,d and confinement/span geometry / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `transverse_cage` | Effective legs, pitch, first tie, hooks and supported bars / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `concrete_contribution` | Vc branch and special-region evidence / not_applicable | Identity and revision are exact; no numeric coercion. Source: Qualified design method. |

**Engineering prerequisites:** `CHK-132`, `CHK-135`.

#### Preserved implementation recipe

1. Define end-confinement and span regions from physical support faces.
2. Calculate required Asw/s and mechanical resistance in each region.
3. Assess the actual stirrup diameter, pitch and leg arrangement against capacity and detailing requirements.

**Output:** Beam transverse-design result and regional stirrup specification.

**Acceptance:** Shear resistance, steel area, pitch and physical legs are verified together in every required region.

**Expected instance key:** `beam_unique_id`, `confinement_or_span_region`, `tie_line`, `cage_revision`, `demand_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/rebar_selection.py::evaluate_beam_stirrups` | Confinement/span stirrup capacity, minimum ratio, pitch and 2h zone reference. |

**Registered stages:** `beam-r10-live`. **Existing GAP references:** `GAP-011`, `GAP-012`, `GAP-014`.

**Inspected implementation:** Supported beam transverse scenarios evaluate capacity and pitch/area requirements.

**Remaining work:** Qualify full Ve, concrete-contribution branch, actual leg topology, physical regions and anchorage.

**Negative scenario to preserve:** Use span spacing in an end-confinement region; sufficient total steel area must not hide the spacing violation.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-136` preserves example provenance and coverage.

### CHK-137 — Beam combined torsion and shear

**Scope:** Beam cut, compatible torsion/shear state and cage. **Golden example:** `GE-CHK-137` (SOURCE_RECALC).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 8.2; equations 8.11, 8.13, 8.15, 8.16, 8.17, 8.18, 8.19. Equilibrium versus compatibility torsion and supported closed-tie geometry; same-cut concurrent shear and torsion are required.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `concurrent_shear_torsion` | Same-cut Vd and Td / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `beam_section` | Web width, effective depth and torsional geometry / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `closed_tie_geometry` | Ae,ue and outer closed perimeter / Ae: mm^2; ue: mm | Internal crossties are not part of the outer torsion perimeter. Source: Selected cage geometry. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `torsion_class` | Equilibrium/compatibility and negligibility branch / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved structural model. |

**Engineering prerequisites:** `SRC-005`, `CHK-132`, `CHK-135`, `CHK-136`.

#### Preserved implementation recipe

1. Determine the applicable torsion branch and demand role.
2. Apply the accepted combined torsion/shear method through one existing calculation owner.
3. Compare required transverse and longitudinal contributions with the selected physical cage.

**Output:** Beam torsion/shear result and reinforcement contributions.

**Acceptance:** The supported interaction method verifies closed transverse and longitudinal reinforcement.

**Expected instance key:** `beam_unique_id`, `physical_cut_key`, `combination_id`, `step_identity`, `torsion_class`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-012`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No combined beam torsion/shear design owner was found. Reading TLngRebar targets does not implement the interaction or torsion cage.

**Negative scenario to preserve:** Silently assume zero torsion and close the beam through shear alone; the absent torsion assessment must remain visible.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-137` preserves example provenance and coverage.

### CHK-138 — Beam cracking and deflection

**Scope:** Beam span, service combination and time effects. **Golden example:** `GE-CHK-138` (DERIVED_BENCHMARK).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 13.2; Tables 13.1 to 13.3; 13.3; Table 13.4; equations 13.1, 13.2, 13.3, 13.4, 13.5. Service loads, cracked stiffness, load duration and crack exposure; any project limit stricter than the code is separately labelled.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `service_demand` | Unfactored service state / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `beam_section` | Service section, effective depth and span / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `selected_cage` | Actual or explicitly selected reinforcing cage / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `stiffness_materials` | Ec,Es and cracked/gross inertia / E: MPa; I: mm^4 | Use service stiffness and the selected crack/time-dependent method. Source: Material and section properties. |
| `duration_and_environment` | Load duration, sustained fraction and crack exposure / not_applicable | Identity and revision are exact; no numeric coercion. Source: Project specification. |
| `service_limits` | Deflection and crack limits / mm or explicit span ratio | Code and stricter project policy are identified separately. Source: Applicable serviceability branch. |

**Engineering prerequisites:** `CHK-130`, `CHK-132`.

#### Preserved implementation recipe

1. Build the service-load family separately from strength demands.
2. Calculate short- and long-term response with the accepted cracked-stiffness and time-dependent method.
3. Compare deflection and cracking criteria at the required positions and service states.

**Output:** Beam serviceability result with time/load contributions.

**Acceptance:** Service roles, effective stiffness and sustained-load effects reproduce independent serviceability values.

**Expected instance key:** `beam_unique_id`, `service_combination_id`, `duration_class`, `crack_or_deflection_direction`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete beam cracking/deflection calculation owner was found in the inspected source.

**Negative scenario to preserve:** Use strength combinations as service states or gross inertia as cracked stiffness without justification; acceptance must fail.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-138` preserves example provenance and coverage.

### CHK-139 — Beam anchorage and continuity

**Scope:** Individual beam bar, support face and anchorage region. **Golden example:** `GE-CHK-139` (DERIVED_BENCHMARK).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 9.1.1; 9.1.2; equations 9.1. Applicable bond, bar/hook configuration and available development geometry.
- **Turkish Building Earthquake Code (TBDY), 2018.** 7.4.3.1. Beam-joint anchorage and continuation under the actual joint geometry and reinforcement direction.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `anchored_bars` | Diameter, bend/hook geometry, face and bar continuation / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `available_length` | Physical development/anchorage space / mm | Nonnegative physical magnitude; retain the declared unit. Source: Joint/support geometry. |
| `bond_branch` | Bond position, confinement and hook eligibility / not_applicable | Identity and revision are exact; no numeric coercion. Source: Applicable detailing evidence. |

**Engineering prerequisites:** `CHK-132`, `CHK-147`.

#### Preserved implementation recipe

1. Identify the physical start, termination and continuation regions of each bar.
2. Calculate required anchorage or lap length under the applicable branch.
3. Compare actual available length, hook and placement conditions with the requirement.

**Output:** Beam anchorage/continuity result and bar-specific detail ledger.

**Acceptance:** Actual bar continuity, available development length and joint geometry establish anchorage and splice adequacy.

**Expected instance key:** `beam_unique_id`, `joint_id`, `bar_id`, `anchorage_direction`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-011`, `GAP-012`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete bar-specific beam anchorage/continuity calculation owner was found.

**Negative scenario to preserve:** Accept an anchorage that cannot physically fit merely because a formula length exists; geometric acceptance must fail.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-139` preserves example provenance and coverage.

### CHK-140 — Wall segment to pier mapping

**Scope:** Physical wall, shell representation, pier group and cut. **Golden example:** `GE-CHK-140` (CONTRACT_FIXTURE).

#### Specification and applicability

- **YENI engineering source and integration contract, Existing 73-card recipe, 2026-11-18.** Engineering integration contract. Physical wall/arm ownership, shell meshes, piers and common section cuts; a pier name alone does not establish a physical member.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `physical_walls` | Wall/arm roster and ownership / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical model topology. |
| `shell_mesh` | Shell elements and oriented connectivity / not_applicable | Identity and revision are exact; no numeric coercion. Source: Native mesh capture. |
| `pier_assignments` | Pier names and member-to-shell associations / not_applicable | Identity and revision are exact; no numeric coercion. Source: Native pier assignments. |
| `wall_cuts` | Independent physical section cuts / m | Common cut orientation and reference prevent shell/pier double counting. Source: Geometry ledger. |

**Engineering prerequisites:** `SRC-003`, `SRC-004`.

#### Preserved implementation recipe

1. Bind every physical wall to its analytical shell/pier representation.
2. Define orientation, top/bottom side and contribution ownership across openings and cuts.
3. Retain a unique and complete physical-to-analysis mapping for every load/cut.

**Output:** Wall/pier topology ledger.

**Acceptance:** Every physical wall component maps uniquely and completely within its analysis namespace and cut.

**Expected instance key:** `physical_wall_id`, `wall_arm_id`, `analysis_shell_id`, `pier_id`, `physical_cut_key`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

Related source/catalog functions are retained without being counted as calculation owners:

- `src/tbdy_next/wall_geometry.py::bind_wall_geometry` — Observed wall-panel geometry only; physical wall/arm and pier ownership remain unqualified.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-015`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete physical wall-to-shell-to-pier cut ledger was found.

**Negative scenario to preserve:** Join frame and shell objects sharing a name or duplicate pier contributions; the mapping must fail.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-140` preserves example provenance and coverage.

### CHK-141 — Wall axial flexural resistance

**Scope:** Selected wall cage and design cut. **Golden example:** `GE-CHK-141` (DERIVED_BENCHMARK).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** Chapter 7. Applicable wall section equilibrium and strain compatibility with physical boundary/web bars.
- **Turkish Building Earthquake Code (TBDY), 2018.** 7.6.6. Wall axial-flexural design and its applicable seismic branch; the golden single-axis example is deliberately narrower than general wall PMM.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `wall_section` | Actual wall polygon and reference axes / mm | Physical wall axes and any arm coupling are explicit. Source: CHK-140. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `wall_cage` | Boundary and web reinforcement coordinates / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `wall_design_state` | Physical signed force state / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |

**Engineering prerequisites:** `SRC-005`, `CHK-140`, `CHK-142`, `CHK-143`.

#### Preserved implementation recipe

1. Model the actual wall geometry and selected reinforcement distribution.
2. Evaluate the demand through the applicable existing axial-flexural capacity owner.
3. Record capacity, utilization and numerical quality for every case/cut.

**Output:** Wall axial-flexural result.

**Acceptance:** The demand, web/boundary cage and supported capacity-method scope are independently verified.

**Expected instance key:** `physical_wall_id`, `physical_cut_key`, `combination_id`, `bending_direction`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-015`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete wall-specific N-M demand/cage/capacity owner was found; the column section solver is not a verified wall integration.

**Negative scenario to preserve:** Take N and M from different wall cuts; the pair must not be reported as one same-cut design state.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-141` preserves example provenance and coverage.

### CHK-142 — Wall critical and boundary regions

**Scope:** Wall critical height and boundary region. **Golden example:** `GE-CHK-142` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.6.2.1; 7.6.2.2; 7.6.2.3; equations 7.15. Actual wall height, length, critical region and required boundary regions.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `wall_height` | Applicable physical wall height / m | Nonnegative physical magnitude; retain the declared unit. Source: CHK-140. |
| `wall_length` | Wall length in the considered direction / m | Nonnegative physical magnitude; retain the declared unit. Source: CHK-140. |
| `story_regions` | Base, story and discontinuity elevations / m | Use physical story order and actual wall continuity. Source: Physical geometry. |
| `boundary_branch` | Applicable wall end/boundary criteria / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved system/geometry profile. |

**Engineering prerequisites:** `CHK-140`.

#### Preserved implementation recipe

1. Identify effective wall geometry and actual physical ends.
2. Derive critical-region height and boundary requirements using the applicable method.
3. Provide one shared critical/boundary-region artifact to reinforcement and shear consumers.

**Output:** Wall critical-height and boundary-region definitions.

**Acceptance:** Actual wall geometry and system classification establish critical and end-region requirements.

**Expected instance key:** `physical_wall_id`, `critical_height_region`, `boundary_end`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-015`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No wall critical-height/boundary-region owner was found.

**Negative scenario to preserve:** Ignore basement or opening effects on effective geometry; the resulting region must remain unqualified.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-142` preserves example provenance and coverage.

### CHK-143 — Wall horizontal and vertical reinforcement

**Scope:** Wall web, boundary, connection and splice regions. **Golden example:** `GE-CHK-143` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.6.3.1; 7.6.3.3. Applicable wall web and boundary reinforcement; the golden example uses the unreduced 0.0025 branch.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `wall_geometry` | Thickness, length and boundary widths / mm | Web and boundary regions have exclusive physical ownership. Source: CHK-140 and CHK-142. |
| `wall_cage` | Actual or explicitly selected reinforcing cage / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `reinforcement_branch` | Reduced/unreduced web minimum and boundary requirements / not_applicable | Identity and revision are exact; no numeric coercion. Source: Applicable normative profile. |

**Engineering prerequisites:** `CHK-140`, `CHK-142`.

#### Preserved implementation recipe

1. Model web, boundary, connection and splice reinforcement separately.
2. Calculate applicable ratio, pitch and continuity requirements.
3. Bind detailing results to the capacity checks of the same cage revision.

**Output:** Wall reinforcement-detailing result.

**Acceptance:** Selected horizontal/vertical ratios and connection details are assessed using actual physical placement.

**Expected instance key:** `physical_wall_id`, `web_or_boundary_region`, `reinforcement_direction`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-015`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No full wall web/boundary reinforcement detailing owner was found.

**Negative scenario to preserve:** Count web steel as boundary steel or omit a splice region; scope deficiency must remain visible.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-143` preserves example provenance and coverage.

### CHK-144 — Wall capacity shear and resistance

**Scope:** Wall direction, physical cut and earthquake state. **Golden example:** `GE-CHK-144` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.6; equations 7.16, 7.17, 7.18. Applicable wall capacity-shear demand, dynamic amplification and shear-resistance branch.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `wall_force_state` | Physical signed force state / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `wall_capacity` | Same-axis flexural capacity and design demand / kN*m | Same wall, cut, cage and axial state. Source: CHK-141. |
| `wall_shear_geometry` | Effective wall shear area and dimensions / area: mm^2; length: mm | Use the applicable wall direction and physical web. Source: CHK-140. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `amplification_branch` | Dynamic/capacity factors and applicable resistance bound / not_applicable | Identity and revision are exact; no numeric coercion. Source: Qualified wall method. |

**Engineering prerequisites:** `CHK-140`, `CHK-141`, `CHK-143`.

#### Preserved implementation recipe

1. Derive wall capacity-shear demand at the actual cut using its method branch.
2. Calculate applicable concrete, web and boundary reinforcement resistance contributions.
3. Compare Ve, Vr and any brittle limits for every required region/direction.

**Output:** Wall capacity-shear result.

**Acceptance:** Same-cut M/N/V and compatible capacity revision support independent demand/resistance comparisons.

**Expected instance key:** `physical_wall_id`, `physical_cut_key`, `direction`, `combination_id`, `demand_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-015`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No full wall capacity-shear/resistance owner was found.

**Negative scenario to preserve:** Bind critical-region capacity to another cut demand or apply D twice; the result must be rejected.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-144` preserves example provenance and coverage.

### CHK-145 — Coupling beam design

**Scope:** Coupling-beam span, end faces and reinforcement arrangement. **Golden example:** `GE-CHK-145` (DERIVED_BENCHMARK).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.6; equations 7.20a, 7.20b, 7.21. Coupling-beam geometry/force branch, diagonal reinforcement and wall anchorage.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `coupling_beam_geometry` | Clear span, depth, width and wall embedment / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `coupling_beam_state` | Physical signed force state / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `coupling_cage` | Diagonal/longitudinal/transverse bars and anchorage / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `classification_branch` | Diagonal or conventional detailing and demand criteria / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical wall/beam role. |

**Engineering prerequisites:** `CHK-140`, `CHK-143`.

#### Preserved implementation recipe

1. Identify the member as a wall coupling beam and classify its geometry.
2. Select the applicable reinforcement arrangement and force-transfer method.
3. Assess flexure/shear, diagonal reinforcement and anchorage within the same physical detail.

**Output:** Coupling-beam design result.

**Acceptance:** Conventional or diagonal reinforcement is supported by the coupling-beam geometry and demand branch.

**Expected instance key:** `coupling_beam_id`, `diagonal_or_conventional_branch`, `earthquake_sign`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-015`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No coupling-beam classification, diagonal reinforcement and anchorage owner was found.

**Negative scenario to preserve:** Close a short coupling beam requiring special detailing with an ordinary beam check; applicability remains unresolved.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-145` preserves example provenance and coverage.

### CHK-146 — Story shear partition and wall factor

**Scope:** Story cut, direction, sign and structural contribution. **Golden example:** `GE-CHK-146` (CONTRACT_FIXTURE).

#### Specification and applicability

- **YENI engineering source and integration contract, Existing 73-card recipe, 2026-11-18.** Engineering integration contract. Story-shear partition by physical frame, wall and pier ownership at the same cut and compatible load state; no signed sums of independent spectrum extrema.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `story_cut_components` | Compatible signed frame/wall/pier contributions / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `physical_ownership` | Exclusive contributor identity / not_applicable | Identity and revision are exact; no numeric coercion. Source: Frame and wall topology. |
| `reference_frame` | Direction, cut plane and moment reference / m and direction cosines | All contributors are transformed to a common reference before summation. Source: Independent cut geometry. |
| `reference_story_shear` | Independent compatible story shear / kN | Nonnegative physical magnitude; retain the declared unit. Source: Same-case story result. |

**Engineering prerequisites:** `SRC-003`, `SRC-004`, `SRC-005`, `CHK-140`.

#### Preserved implementation recipe

1. Construct all expected structural contributions from the physical census.
2. Deduplicate overlapping shell/pier/frame representations and transform to common axes.
3. Calculate total story shear and wall share using compatible same-cut demand semantics.

**Output:** Story-shear partition result and contributor ledger.

**Acceptance:** The complete expected population reconciles story shear and wall share at one cut and demand meaning.

**Expected instance key:** `physical_story_cut`, `direction`, `case_id`, `step_identity`, `physical_contributor_id`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `GAP-015`.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete same-cut wall/frame/pier story-shear partition owner was found. Column-only alpha qualification is a separate supported subset.

**Negative scenario to preserve:** Remove a wall and compute percentages from the remainder; the expected physical denominator must not shrink.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-146` preserves example provenance and coverage.

### CHK-147 — Joint topology

**Scope:** Physical joint and every incident member end. **Golden example:** `GE-CHK-147` (CONTRACT_FIXTURE).

#### Specification and applicability

- **YENI engineering source and integration contract, Existing 73-card recipe, 2026-11-18.** Engineering integration contract. Physical joint feature for all incident members, end roles, orientation and positive evidence of absent members.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `joint_connectivity` | Independent physical joint/member connectivity / not_applicable | Identity and revision are exact; no numeric coercion. Source: Geometry source. |
| `member_orientation` | End coordinates and local axes / coordinate: m; direction cosine: 1 | Each member has oriented I/J ends and a right-handed frame. Source: Geometry/axis assignment. |
| `member_roles` | Frame beam, column, wall, null/rigid and absence evidence / not_applicable | Identity and revision are exact; no numeric coercion. Source: Structural assignments and physical roster. |

**Engineering prerequisites:** `SRC-003`.

#### Preserved implementation recipe

1. Construct the joint key and physical incident-member roster independently of results.
2. Bind each member end to its correct face and three-dimensional orientation.
3. Classify genuine free edges and roof conditions using positive topology evidence.

**Output:** Joint-topology feature and incident-end map.

**Acceptance:** Three-dimensional identities establish all neighbors, directions, faces and end roles.

**Expected instance key:** `physical_joint_id`, `incident_member_id`, `member_end_role`, `orientation_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/engineering/design_dependencies.py::build_member_dependency_plan` | Independent member/joint dependency roster. |
| `src/tbdy_next/engineering/column_r10_live.py::_build_frame_catalog` | Frame geometry and axes. |
| `src/tbdy_next/engineering/column_r10_live.py::_evaluate_joint_end` | Incident beam/column end classification. |

**Registered stages:** `design-dependencies`, `column-r10`. **Existing GAP references:** `GAP-005`, `GAP-006`, `GAP-012`.

**Inspected implementation:** Physical member/joint roster and supported end topology are present.

**Remaining work:** Qualify actual faces, all three-dimensional orientations and positive absence/exemption evidence.

**Negative scenario to preserve:** Interpret a missing beam record as a genuine beamless edge; topology must remain incomplete without positive absence evidence.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-147` preserves example provenance and coverage.

### CHK-148 — Joint confinement

**Scope:** Joint direction, enclosure class and transverse cage. **Golden example:** `GE-CHK-148` (DERIVED_BENCHMARK).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.5.1; 7.5.2.3. Actual enclosure geometry, beam width relation and joint transverse reinforcement; eccentric geometry requires an explicit supported branch.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `joint_dimensions` | Column and incident beam widths, depths and offsets / mm | Compare widths in the actual joint face direction; retain eccentricity. Source: CHK-147. |
| `joint_transverse_cage` | Joint region ties and crossties / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `enclosure_class` | Evidence for confined/unconfined classification / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical enclosure topology. |

**Engineering prerequisites:** `CHK-121`, `CHK-123`, `CHK-147`.

#### Preserved implementation recipe

1. Determine enclosure in every joint direction from physical beam faces.
2. Measure beam width and effective panel geometry under the applicable rule.
3. Assess confinement and transverse reinforcement for the established enclosure class.

**Output:** Joint-confinement result.

**Acceptance:** Actual joint geometry establishes enclosing faces, beam-width conditions and transverse requirements.

**Expected instance key:** `physical_joint_id`, `joint_face`, `enclosure_class`, `transverse_cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `MAPPED_PARTIAL` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

| Verified source owner | Implemented scope |
| --- | --- |
| `src/tbdy_next/column_engine/joint_kernel.py::width_reference` | Inclusive 0.75 beam-width relation. |
| `src/tbdy_next/column_engine/joint_kernel.py::joint_transverse_reference` | Enclosure-specific Ash/s and spacing/diameter comparisons. |
| `src/tbdy_next/engineering/column_r10_live.py::_evaluate_joint_end` | Observed enclosure classification. |

**Registered stages:** `column-r10`. **Existing GAP references:** `GAP-011`, `GAP-012`, `GAP-014`.

**Inspected implementation:** Width and enclosure-specific transverse-density references exist.

**Remaining work:** Qualify eccentric enclosure/face geometry and actual joint transverse cage/anchorage.

**Negative scenario to preserve:** Treat a narrow or eccentric beam as fully enclosing; the more favorable joint capacity must not be granted.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-148` preserves example provenance and coverage.

### CHK-149 — Slab classification and geometry

**Scope:** Slab panel, span, supports and openings. **Golden example:** `GE-CHK-149` (DERIVED_BENCHMARK).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 11.4.1; equations 11.1. Supported slab type, span/support/opening geometry and conditions of any minimum-depth exemption.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `slab_panel_geometry` | Boundary, thickness, spans, supports and openings / mm or declared m | Panel axes and support-edge classifications are physical. Source: Slab topology. |
| `slab_type` | One-way, two-way, flat slab or other supported type / not_applicable | Identity and revision are exact; no numeric coercion. Source: Structural role. |
| `depth_exemption_conditions` | Adjoining elements and service conditions / not_applicable | Identity and revision are exact; no numeric coercion. Source: Project/detail evidence. |

**Engineering prerequisites:** `SRC-003`.

#### Preserved implementation recipe

1. Separate physical panels using actual support and opening topology.
2. Classify slab type from the structural profile and geometry.
3. Provide consistent geometric features to flexure, serviceability and punching consumers.

**Output:** Slab geometry and type feature.

**Acceptance:** Complete polygons and support topology establish slab classification and applicable dimensions.

**Expected instance key:** `slab_panel_id`, `support_edge_id`, `opening_id`, `slab_type`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete slab panel/type/support/opening geometry owner was found.

**Negative scenario to preserve:** Hide an opening or lost support behind a solid-slab assumption; classification and span decisions must remain unresolved.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-149` preserves example provenance and coverage.

### CHK-150 — Slab flexural reinforcement

**Scope:** Slab design strip/cut, direction and face. **Golden example:** `GE-CHK-150` (DERIVED_BENCHMARK).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 7.1; 11.4.2. Selected slab flexural design method; the golden principal-axis tensor example is not an unqualified generic Wood-Armer implementation.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `shell_moment_tensor` | Signed M11,M22,M12 / kN*m/m | Retain native shell axes, top/bottom sign and the supported transformation method. Source: Same-state shell force results. |
| `slab_geometry` | Thickness, cover and reinforcement directions / mm and degree | Physical top/bottom layers and effective depths remain distinct. Source: CHK-149. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `slab_design_method` | Qualified tensor-to-design-moment method / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved method. |

**Engineering prerequisites:** `SRC-005`, `CHK-149`.

#### Preserved implementation recipe

1. Transform shell moments to recorded design directions and physical strips/cuts.
2. Apply the accepted design-moment method separately to support/span and top/bottom regions.
3. Bind required reinforcement to selected layer geometry and detailing requirements.

**Output:** Slab flexural-design result.

**Acceptance:** Local axes, shell moments and the selected top/bottom design method explicitly establish reinforcement demand.

**Expected instance key:** `slab_panel_id`, `physical_strip_or_shell_cut`, `direction`, `top_or_bottom`, `combination_id`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No shell-moment-to-selected-slab-reinforcement owner was found.

**Negative scenario to preserve:** Omit M12 or reverse shell axes; an independent transformation example must detect incorrect reinforcement demand.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-150` preserves example provenance and coverage.

### CHK-151 — Slab punching shear

**Scope:** Column/wall/slab connection and critical perimeter. **Golden example:** `GE-CHK-151` (SOURCE_RECALC).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.11.8; 7.11.9. Slab-column punching with actual critical perimeter, load-transfer moment and gammaf; edge/corner/opening branches remain distinct.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `punching_shear` | Net force crossing the actual critical perimeter / kN | Nonnegative physical magnitude; retain the declared unit. Source: Compatible slab-column load state. |
| `transfer_moments` | Same-state unbalanced moments / kN*m | Moments refer to the same centroid and axes as the perimeter stress model. Source: Compatible joint/slab demand. |
| `critical_perimeter` | Geometry, centroid, section properties and openings / length: mm; inertia: mm^4 | Edge/corner/opening reductions are explicit; gammaf transfers the qualified moment fraction. Source: Physical slab-column geometry. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |

**Engineering prerequisites:** `SRC-005`, `CHK-149`, `CHK-150`.

#### Preserved implementation recipe

1. Construct the critical perimeter from actual connection geometry, openings and edges.
2. Convert shear and moment transfer to the applicable perimeter demand distribution.
3. Compare punching demand, resistance and supported reinforcement/detailing method.

**Output:** Slab punching result with critical-perimeter geometry.

**Acceptance:** Actual transferred loads and opening/edge effects establish the critical perimeter and punching demand.

**Expected instance key:** `slab_column_joint_id`, `critical_perimeter_id`, `combination_id`, `step_identity`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No physical slab punching-perimeter and moment-transfer owner was found.

**Negative scenario to preserve:** Use an interior-column perimeter at an edge or ignore an opening deduction; resistance must not be overstated.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-151` preserves example provenance and coverage.

### CHK-152 — Slab deflection and cracking

**Scope:** Slab panel, service state and time effects. **Golden example:** `GE-CHK-152` (SOURCE_RECALC).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 13.2; Table 13.3; 13.3; Table 13.4; equations 13.3, 13.5. Slab serviceability under qualified service loads, cracked stiffness, duration and environmental limits.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `service_loads` | Qualified service membrane/moment and load history / force: kN/m; moment: kN*m/m | Separate strength and service combinations; retain top/bottom direction. Source: Service role book and source. |
| `slab_stiffness` | Cracked/gross stiffness and time-dependent factors / E: MPa; I per strip: mm^4; factor: 1 | Same selected section and reinforcement as the service result. Source: Slab section/cage. |
| `slab_cage` | Actual or explicitly selected reinforcing cage / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `service_conditions` | Span/support, duration and environment / not_applicable | Identity and revision are exact; no numeric coercion. Source: Applicable service profile. |

**Engineering prerequisites:** `CHK-149`, `CHK-150`.

#### Preserved implementation recipe

1. Establish the displacement reference plane and support-movement contribution.
2. Calculate short/long-term deflection and crack measures using the accepted method.
3. Record the applicable service limit and governing state at each required panel/location.

**Output:** Slab serviceability result.

**Acceptance:** Appropriate stiffness, sustained loading and reinforcement establish service deflection/cracking demand.

**Expected instance key:** `slab_panel_id`, `service_combination_id`, `direction`, `duration_class`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete slab cracking/deflection owner was found.

**Negative scenario to preserve:** Compare raw maximum Uz with a deflection limit without service, support or time context; closure must be withheld.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-152` preserves example provenance and coverage.

### CHK-153 — Diaphragm in-plane transfer

**Scope:** Diaphragm region, collector, chord and connection. **Golden example:** `GE-CHK-153` (DERIVED_BENCHMARK).

#### Specification and applicability

- **Turkish Building Earthquake Code (TBDY), 2018.** 7.11.5. Diaphragm collector/chord/interface force and anchorage; applicable resistance includes the separately identified tension and friction terms.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `diaphragm_demands` | Collector/chord/interface membrane forces / kN or explicitly kN/m | Use the same physical cut and load state; conversion of line force to resultant is explicit. Source: Compatible diaphragm result. |
| `collector_and_interface_rebar` | Anchored tension and interface bars / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `friction_coefficient` | Applicable interface coefficient / 1 | Nonnegative physical magnitude; retain the declared unit. Source: Evidenced interface condition. |
| `anchorage_path` | Force transfer into adjoining members / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical detailing. |

**Engineering prerequisites:** `SRC-005`, `CHK-149`.

#### Preserved implementation recipe

1. Define the horizontal force path using physical regions and connections.
2. Convert membrane forces into collector/chord and interface demands.
3. Assess capacity and detailing continuity of regions and connections under the same load state.

**Output:** Diaphragm-transfer result and load-path ledger.

**Acceptance:** In-plane force paths, connection demand/capacity and physical continuity are verified together.

**Expected instance key:** `diaphragm_id`, `collector_chord_or_interface_id`, `direction`, `load_state_id`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No diaphragm collector/chord/interface strength owner was found. A diaphragm assignment/source-linkage check is a different scope.

**Negative scenario to preserve:** Treat a rigid-diaphragm assignment as proof of collector/chord resistance; the omitted connection calculation must remain open.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-153` preserves example provenance and coverage.

### CHK-154 — Foundation geometry

**Scope:** Foundation object, superstructure interface and ground profile. **Golden example:** `GE-CHK-154` (SOURCE_RECALC).

#### Specification and applicability

- **YENI engineering source and integration contract, Existing 73-card recipe, 2026-11-18.** Engineering integration contract. Foundation geometry, physical interface, soil support and design-critical sections; a separate foundation model retains its own source identity.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `foundation_geometry` | Foundation/slab/pedestal/column geometry and soil support / m or explicit mm | Retain a distinct foundation model and coordinate system. Source: Foundation model source. |
| `interface_map` | Superstructure-to-foundation physical correspondence / not_applicable | Identity and revision are exact; no numeric coercion. Source: Explicit model interface ledger. |
| `critical_sections` | Independent shear/punching/flexure section inventory / not_applicable | Identity and revision are exact; no numeric coercion. Source: Physical geometry derivation. |

**Engineering prerequisites:** `SRC-002`, `SRC-003`, `CHK-114`.

#### Preserved implementation recipe

1. Create distinct source identities for the foundation and superstructure models.
2. Match load-transfer points by coordinates and physical member identity.
3. Provide foundation type/geometry to geotechnical and reinforced-concrete consumers.

**Output:** Foundation-geometry feature and superstructure-interface map.

**Acceptance:** A separate physical-model identity and matched transfer points establish foundation geometry.

**Expected instance key:** `foundation_model_id`, `foundation_member_id`, `interface_id`, `critical_section_id`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No distinct foundation-model geometry/interface owner was found.

**Negative scenario to preserve:** Join another foundation model by a matching name; incompatible thicknesses or coordinates must expose the identity mismatch.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-154` preserves example provenance and coverage.

### CHK-155 — Foundation soil pressure

**Scope:** Foundation contact region, load state and geotechnical limit. **Golden example:** `GE-CHK-155` (SOURCE_RECALC).

#### Specification and applicability

- **YENI engineering source and integration contract, Existing 73-card recipe, 2026-11-18.** Engineering integration contract. Soil pressure compared with a geotechnical limit from the same limit state, contact model and loading basis; tensile contact cannot be silently retained in compression-only soil.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `contact_pressures` | Signed contact pressure field / kPa | Compression sign and contact model are explicit; no silent tensile bearing in compression-only support. Source: Foundation analysis result. |
| `geotechnical_limit` | Design or allowable bearing limit / kPa | Same limit state, safety-factor convention and load basis as demand. Source: Approved geotechnical report. |
| `contact_model` | Linear full contact or compression-only nonlinear support / not_applicable | Identity and revision are exact; no numeric coercion. Source: Native foundation model/settings. |
| `foundation_load_state` | Physical signed force state / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |

**Engineering prerequisites:** `SRC-004`, `SRC-005`, `CHK-154`, `CHK-158`.

#### Preserved implementation recipe

1. Define the physical contact region and compression/separation model.
2. Bind the geotechnical comparison limit to the applicable load and limit-state basis.
3. Compare stresses and contact-area equilibrium under compatible states.

**Output:** Foundation soil-pressure result and contact-area summary.

**Acceptance:** Stress/contact response and the geotechnical limit share model, area and accepted load-state basis.

**Expected instance key:** `foundation_member_id`, `contact_cell_or_region`, `limit_state`, `combination_id`, `contact_model_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No contact-model/geotechnical-limit pressure comparison owner was found.

**Negative scenario to preserve:** Assume full compression under uplift or use a limit from another limit state; do not grant acceptance.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-155` preserves example provenance and coverage.

### CHK-156 — Foundation shear and punching

**Scope:** Foundation critical section or punching perimeter. **Golden example:** `GE-CHK-156` (SOURCE_RECALC).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 8.3.1; 8.4. Applicable foundation one-way/punching shear critical section, net load and geometry-dependent resistance branch; retain wall-load branches separately.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `net_shear` | Force minus qualified opposing pressure inside the cut / kN | Nonnegative physical magnitude; retain the declared unit. Source: Same-state foundation loading and soil pressure. |
| `critical_geometry` | One-way section or punching perimeter and effective depth / mm | Actual support/pedestal/edge/wall geometry selects the branch. Source: CHK-154. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `resistance_branch` | Applicable one-way or punching method / not_applicable | Identity and revision are exact; no numeric coercion. Source: Qualified foundation method. |

**Engineering prerequisites:** `CHK-154`, `CHK-155`.

#### Preserved implementation recipe

1. Construct one-way shear cuts and punching perimeters from actual loaded faces.
2. Derive net demand from superstructure loads and soil reactions within the section/perimeter.
3. Evaluate shear/punching resistance and required detailing using the selected foundation cage.

**Output:** Foundation shear/punching result.

**Acceptance:** Physical geometry, column/wall effects and contact reactions independently establish net demand.

**Expected instance key:** `foundation_member_id`, `critical_section_id`, `shear_branch`, `combination_id`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No full foundation one-way/punching shear owner was found.

**Negative scenario to preserve:** Treat the full superstructure reaction as critical-section shear without accounting for enclosed soil reaction; equilibrium must detect the error.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-156` preserves example provenance and coverage.

### CHK-157 — Foundation reinforcement

**Scope:** Foundation cut, direction, face and cage. **Golden example:** `GE-CHK-157` (DERIVED_BENCHMARK).

#### Specification and applicability

- **TS 500: Requirements for Design and Construction of Reinforced Concrete Structures, February 2000; inspected amendment sources T1 (2001) and T2 (2002) remain separately identified.** 7.1; 9.1.2; 10.4.3; 11.4.5; 13.3.2. Foundation reinforcement, development and service checks by branch. Any minimum ratio based on gross b*h in the golden benchmark is an explicit project policy, not a universal code substitution.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `foundation_flexure` | Same-state design moments by strip/direction / kN*m or explicitly kN*m/m | Retain top/bottom face, local axes and strip width. Source: Qualified foundation result. |
| `foundation_section` | Width, total/effective depth and cover / mm | Convert native t2/t3 to local dimensions once. M2 bends about local axis 2; M3 bends about local axis 3. Do not infer major/minor axes from a label. Source: Geometry ledger. |
| `foundation_cage` | Actual or explicitly selected reinforcing cage / bar diameter/coordinates/cover: mm; area: mm^2 | Bars have physical coordinates and face identities in the section frame. TEMPLATE, PROPOSED and SELECTED are distinct roles. Source: Reinforcement revision ledger. |
| `material_strengths` | Applicable concrete and steel strengths / MPa = N/mm^2 | Characteristic and design strengths remain distinct; material factors and edition are explicit. Source: Assigned material ledger. |
| `minimum_and_service_policy` | Code branch, explicit project minima and service limits / not_applicable | Identity and revision are exact; no numeric coercion. Source: Approved profile. |

**Engineering prerequisites:** `CHK-154`, `CHK-155`, `CHK-156`.

#### Preserved implementation recipe

1. Determine design moment and required As at every necessary cut and face.
2. Select bar layout satisfying cover, clear spacing and anchorage.
3. Record minimum reinforcement and service requirements alongside flexural capacity.

**Output:** Foundation reinforcement-design result.

**Acceptance:** Flexure, serviceability, anchorage and minimum detailing are assessed together in the same foundation model.

**Expected instance key:** `foundation_member_id`, `strip_or_region`, `direction`, `top_or_bottom`, `cage_revision`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No foundation reinforcement selection/detailing/service owner was found.

**Negative scenario to preserve:** Move bottom steel into a top-tension demand or omit anchorage; partial flexural adequacy must not establish complete acceptance.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-157` preserves example provenance and coverage.

### CHK-158 — Superstructure foundation same-cut transfer

**Scope:** Superstructure/foundation interface and compatible load state. **Golden example:** `GE-CHK-158` (DERIVED_BENCHMARK).

#### Specification and applicability

- **YENI engineering source and integration contract, Existing 73-card recipe, 2026-11-18.** Engineering integration contract. Cross-model load transfer with Ftarget=R Fsource and Mtarget=R Msource+r cross Ftarget at a common physical reference; preserves combination and generation lineage.

The references preserve the existing normative scope. They do not constitute a new interpretation approval.

#### Inputs, units and axes

| Contract field | Quantity / unit | Sign, axis and source rule |
| --- | --- | --- |
| `source_interface_state` | Superstructure interface forces and moments / force: kN; moment: kN*m | Keep one cut, element side, combination, step, initial state and axis frame. Preserve signed N,V2,V3,T,M2,M3; convert native P to compression-positive N explicitly. An unsigned spectrum envelope is a different type. Source: SRC-003, SRC-004, SRC-005. |
| `rotation_matrix` | Source-to-target orthonormal frame rotation / 1 | Right-handed direction cosine matrix; check orientation and units. Source: Explicit interface geometry. |
| `reference_offset` | Source-to-target reference vector / m | Offset direction is explicitly defined for moment transport r cross Ftarget. Source: Physical interface geometry. |
| `state_correspondence` | Case, combination, generation and interface identity across models / not_applicable | Identity and revision are exact; no numeric coercion. Source: Immutable transfer ledger. |

**Engineering prerequisites:** `SRC-004`, `SRC-005`, `CHK-114`, `CHK-154`.

#### Preserved implementation recipe

1. Bind both models by common interface coordinates and member keys, and verify load/geometry revision compatibility while preserving distinct generation identities.
2. Transform transferred forces and moments of the same load state to a common reference.
3. Check member-level and whole-interface equilibrium and create the transfer receipt.

**Output:** Superstructure-foundation transfer result and force/moment residuals.

**Acceptance:** Every column/wall transfer, coordinate transformation and total force/moment balance is traced across distinct model generations through an explicit compatibility binding.

**Expected instance key:** `source_model_id`, `target_model_id`, `physical_interface_id`, `combination_id`, `step_identity`, `generation_pair`.

The expected roster is frozen independently of successful result rows. Missing, blocked or ambiguous keys remain in the denominator; duplicated rows do not replace missing keys. This package does not claim a complete runtime instance ledger.

#### Existing owner and remaining integration

**Current local tree:** `NOT_INSPECTED`; owner `UNMAPPED`. **Inspected published snapshot:** `UNMAPPED` at `b255c3030c09c88a17bbec766fc2bb22682ad027`.

**Calculation owner:** `UNMAPPED` for the full recipe scope in the inspected source.

**Registered stages:** `UNMAPPED`. **Existing GAP references:** `UNMAPPED`; no new GAP is invented.

**Inspected implementation:** No complete calculation owner for this recipe scope was identified in the inspected source.

**Remaining work:** No complete cross-model same-cut force/moment transfer owner was found.

**Negative scenario to preserve:** Join unrelated or differently revised superstructure reactions and foundation contact results; a matching filename or apparent balance must not hide an incompatible transfer.

The package records schema/identity checks separately from independent arithmetic, production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance. Execution not performed at a level is `NOT_RUN`; this card itself closes no engineering check.

**Evidence:** `CHECK_MAPPING.json` records full source hashes, exact symbols and the source-card locator; `GOLDEN_CASES.json#GE-CHK-158` preserves example provenance and coverage.



## Appendix B — Formula register and method branches


**Review reference date:** 18 November 2026. This appendix preserves the earlier engineering formula and condition register in English. **PDF page** means the physical page counted from one in the file; **printed page** means the page number printed on the page. Formula readings are tied to the identified source copies. Software ordering, mathematical enclosure rules and project interpretation choices are identified separately.

This appendix is a reference for the existing calculation owners. Displayed formulas are explanatory text. They are not expressions to be evaluated dynamically by the application. Translating or packaging the register does not execute a production check or grant engineering acceptance.

### 1 Source identity and unit contract

| Source | Reviewed copy | File SHA-256 |
|---|---|---|
| TS 500, source GE-S16 | `TS500.pdf`, 83 physical PDF pages. Cover: February 2000, first edition. T1: 6 February 2001, PDF pp.76-78. T2: April 2002 / board date 19 April 2002, PDF pp.79-83. These are the amendments visible in the supplied copy. | `d925114d01a1de2baee63738bc0da0112b547b58526c3394843c36ee66722d44` |
| TBDY 2018, source GE-S09 | `20180318M1-2-1.pdf`, 416 physical PDF pages; the user-supplied copy of the annex published in the Official Gazette on 18 March 2018. | `8d3a9a463d4a534ec2c6834c557b5f706e2ad976c2d6837f6c9b6242e38a6bb2` |

The TS 500 edition is recorded as “2000 plus the T1/T2 amendments present in the supplied copy.” The file is not automatically identified as 2014/T3 or as a current consolidated standard. `CodeEditionManifest` records the edition, amendment list and interpretation for each rule. Where an included amendment changes the relevant main clause, the amended text governs that source reading. The column, beam and shear equations below were checked against this copy in the preceding review.

Internal calculation units are N-mm-MPa. A kN-m external source is converted once. Empirical expressions containing `sqrt(fck)` must use their stated MPa and mm units. `fck`, `fyk` and `fywk` are characteristic strengths; `fcd`, `fctd`, `fyd` and `fywd` are design strengths. They are not interchangeable. `Nd` is the axial force in the section's combination; `Ndm` is the largest compression in the specified G+Q+E family; `ln` is physical clear/free length; and `lk=k ln` is effective length.

The TS 500 slenderness symbols `M1/M2` represent the two end moments. CSI `M2/M3` represent moments about two different local axes. The domain uses separate fields such as `M_end_small`, `M_end_large`, `moment_about_local_2` and `moment_about_local_3`. The distinction remains visible throughout the calculation trace.

### 2 Analysis model and second order inputs

| Operation | Verified rule and application | Source |
|---|---|---|
| Effective stiffness assignments | Use both components of the Table 4.2 factors. Their scope is the analysis of loads included in earthquake combinations. Resolve member assignments and section defaults together to obtain the actual effective factor. | TBDY 4.5.8.1-3, PDF 67 / printed 46 |
| Line-element stiffness | Bending/shear: coupling beam `0.15/1.00`; frame beam `0.35/1.00`; frame column `0.70/1.00`; equivalent line-element wall `0.50/0.50`. | TBDY Table 4.2, PDF 68 / printed 47 |
| Shell and membrane stiffness | In-plane axial/shear: wall `0.50/0.50`, basement wall `0.80/0.50`, slab `0.25/0.25`. Out-of-plane bending/shear: wall `0.25/1.00`, basement wall `0.50/1.00`, slab `0.25/1.00`. | Same table |
| Mass | `w_j=w_G,j+n w_Q,j`; `m_j=w_j/g`. The occupancy classification supplies n. Include 30% of roof snow; fixed industrial equipment uses n=1; crane lifted load is excluded from storey weight. Mass participation and TS 498 live-load reduction are separate fields. | TBDY 4.5.9.2, Eq.4.16 and Table 4.3, PDF 68 / printed 47 |
| Diaphragm transfer | A2/A3 cases, systems for which a rigid-diaphragm assumption is inapplicable, and reinforced-concrete flat-slab systems require the applicable two-dimensional finite-element modelling route. Transfer to a vertical member under a rigid diaphragm is derived from the difference between its shears above and below the floor. Transition-storey transfer is evaluated separately. | TBDY 4.5.6.2-5 and 4.5.7, PDF 67 / printed 46 |
| Global second order indicator | `theta_II,i,X=Delta_i,avg,X * sum(k=i..N,w_k)/(V_i,X h_i)`. Use the complete storey population in each earthquake direction and the mean reduced interstorey displacement. | TBDY 4.9.2.1, Eq.4.35, PDF 77 / printed 56 |
| Global magnification | If `theta_max<=0.12 D/(Ch R)`, this method requires no additional global magnification. Otherwise `beta_II=max(1,0.88+(Ch R/D) theta_max)`. Reinforced concrete uses `Ch=0.5`; buildings with steel/composite columns use `Ch=1`. Evaluate X/Y separately. Apply the upper-building scope prescribed for the defined buildings with rigid perimeter basements. | TBDY 4.9.2.2-4, Eqs.4.36-37, PDF 78 / printed 57 |

Analysis-model stiffness effects, local TS 500 `EI`, and member stiffness used in effective-length calculations serve different purposes. Substituting Table 4.2's `0.70Ig` for `Ic` in Eq.7.20 and applying another reduction changes the equation. For every demand, retain `analysis_order`, `global_PDelta_effect`, `member_Pdelta_effect`, `stiffness_state`, the load case, and the transformation sequence.

### 3 Column axial limits eccentricity and reinforcement

| Operation | Formula or condition and application | Source |
|---|---|---|
| Minimum eccentricity | `emin=15+0.03 h` mm; h is the section dimension in the bending plane. Evaluate each column bending axis against `M_floor=Nd emin`, using axial force and moment from the same load state. Raise the absolute signed moment to this floor. At zero moment, both signs may be represented as separate scenarios. | TS 500 6.3.10, Eq.6.16, PDF 27 / printed 20; 7.6.2.5, PDF 34 / printed 27 |
| TS 500 compression limit | `Nd<=0.90 fcd Ac`. Record the utilization and actual Nd with the combination result. | TS 500 7.4.1, Eq.7.7, PDF 30 / printed 23 |
| TBDY column area limit | `Ac>=Ndm/(0.40 fck)`. Ndm is the largest compression under G+Q+E, including the applicable TS 498 live-load reduction. Use the physical combination role rather than a name prefix. | TBDY 7.3.1.2, PDF 135 / printed 114 |
| High-ductility dimensions | Minimum rectangular dimension 300 mm; minimum circular diameter 350 mm. | TBDY 7.3.1.1, PDF 135 / printed 114 |
| Longitudinal reinforcement | `0.01<=Ast/Ac<=0.04`; total ratio in a lap region `<=0.06`; longitudinal bar diameter at least 14 mm; at least six bars in a circular section. The conditional TS 500 0.005 exception does not remove the TBDY 0.01 floor. | TBDY 7.3.2.1-2, PDF 135 / printed 114; TS 500 7.4.1, PDF 30-31 / printed 23-24 |
| Confinement length | At each end, `lo>=max(ln/6,1.5*b_max,500 mm)`; at the lower end of a cantilever, `lo>=2*b_max`. Measure from the slab top or underside of the deeper beam as applicable. Retain extension into the foundation in the physical region definition. | TBDY 7.3.4.1, PDF 136 / printed 115 |
| Confinement vertical spacing and legs | `phi_t>=8 mm`; `50<=s<=min(b_min/3,150,6*phi_long)` mm. Horizontal distance between transverse legs/crossties `a<=25*phi_t`. Continuous circular spiral pitch `<=min(Dcore/5,80 mm)`. | TBDY 7.3.4.1(a), PDF 136 / printed 115 |
| Rectangular confinement area | `Ash_req=max[0.30 s bk (Ac/Ack-1) fck/fywk,0.075 s bk fck/fywk]`, with separate bk in the two directions. Use the full value for `Nd>0.20Ac fck`; use at least two thirds for `Nd<=0.20Ac fck`. Obtain provided area in each direction from actual leg/crosstie topology. | TBDY 7.3.4.1(b,d), Eq.7.1, PDF 136-137 / printed 115-116 |
| Circular confinement | `rho_s>=max[0.45(Ac/Ack-1)fck/fywk,0.12fck/fywk]`; the low-Nd branch permits two thirds. Provide it through the actual circular confining reinforcement. | TBDY 7.3.4.1(c,d), Eq.7.2, PDF 136-137 / printed 115-116 |
| Middle region | `phi_t>=8 mm`; `s<=min(b_min/2,200 mm)`; `a<=25phi_t`. Also apply TS 500 detailing: tie diameter at least one third of the largest longitudinal diameter, `s<=min(12phi_long,min,200 mm)`, and spacing between laterally restrained longitudinal bars at most 300 mm. | TBDY 7.3.4.2, PDF 137 / printed 116; TS 500 7.4.1, PDF 31 / printed 24 |
| Longitudinal splices | Locate laps in the middle third of the clear height; `l_lap>=lb`; over the lap, `s<=min(b_min/3,150 mm)`. At storey section changes the bar slope is at most 1/6. Larger changes and upper-storey ends require the applicable special anchorage `>=max(1.5lb,40phi)` and a 12phi hook. | TBDY 7.3.3, PDF 135-136 / printed 114-115 |

Reinforcement verification includes more than `nlegs*bar_area`. Evaluate each bar coordinate, enclosing hook/crosstie, successive lateral-restraint spacing, cover, clear core dimension, bar conflicts and actual spacing along each region. `Ack` is the core area bounded by the outer edges of the transverse reinforcement. Bind the corresponding bk definition to the same source geometry. Topology and area produce distinct results.

### 4 Column slenderness and TS 500 moment magnification sequence

1. **System and method.** Select the approximate method's scope and check `lk/i<=100` for the stated constant-section, constant-axial-force column case. Construct `ln` from supports, end faces and actual clear length. Evaluate the two bending directions independently. [TS 500 7.6.1-2, PDF 31 / printed 24]
2. **Sway classification.** The braced/non-sway branch can be used where the difference between second order and first order end moments under the same loads and assumptions is at most 5%. The alternative indicator is `phi=1.5 Delta_i sum(Ndi/li)/Vfi<=0.05`. This source copy specifies uncracked sections and the adverse result of G+Q+E and G+1.3Q+1.3W. Use a separately recorded analysis for this indicator; it is not synonymous with TBDY theta. [7.6.2.1, Eq.7.13, PDF 31-32 / printed 24-25]
3. **End restraint.** At each end, `alpha_end=sum(I/l)_columns / sum(I/l)_beams`. Include beams in the relevant bending plane. Use the full column section, cracked beam section and flange for a flanged beam. If a more reliable calculation is absent, the stated approximation is `Icr=0.5Ig` for beams. Order the end values as `alpha1<=alpha2`. These restraint alphas are separate fields from the storey SCWB alpha. [TS 500 symbols, PDF 28 / printed 21; 7.6.2.2, Eq.7.16, PDF 32 / printed 25]
4. **Effective length.** Non-sway branch: `k=min[0.7+0.05(alpha1+alpha2),0.85+0.05alpha1,1]`; where this branch is not calculated, use k=1. Sway branch: `alpha_m=(alpha1+alpha2)/2`; for `<2`, `k=(20-alpha_m)/20 * sqrt(1+alpha_m)`; for `>=2`, `k=0.9sqrt(1+alpha_m)`. The one-end-hinged sway-column branch is `k=2+0.3alpha2`. Then `lk=k ln`. [Eqs.7.14-16, PDF 32 / printed 25]
5. **Slenderness.** `i=sqrt(Ic/Ac)`. Permitted approximations are 0.30 times the rectangular dimension in the bending direction and 0.25 times the circular diameter. Slenderness may be neglected in the non-sway branch for `lk/i<=min[34-12(M_end_small/M_end_large),40]`; in the sway branch the limit is `lk/i<=22`. The end-moment ratio is positive for single curvature and negative for double curvature. Raw ETABS I/J signs alone do not establish that classification. [7.6.2.3, Eqs.7.17-18, PDF 33 / printed 26]
6. **Creep ratio.** For vertical-load column calculation in the non-sway system, `Rm=Ngd/Nd`; for the whole sway storey, `Rm=sum(Vgd)/sum(Vd)`. Derive sustained-load contributions from the original load components. [Eqs.7.22-23, PDF 33 / printed 26]
7. **Stiffness and Euler load.** For selected reinforcement, `EI=(0.2EcIc+EsIs)/(1+Rm)`; alternatively use the explicitly selected branch `EI=0.4EcIc/(1+Rm)`. Then `Nk=pi² EI/lk²`. Is is the longitudinal reinforcement's second moment of area about the member centroid. A cage revision requires recalculation of Is, EI, Nk and every dependent demand. [Eqs.7.19-21, PDF 33 / printed 26]
8. **Local magnification.** `Cm=max(0.4,0.6+0.4 M_end_small/M_end_large)`; use Cm=1 when a transverse load acts between the ends. `beta=max[1,Cm/(1-1.3Nd/Nk)]`; `Md=beta M_end_large`. Apply the minimum-eccentricity floor to `M_end_large` first. The denominator must remain positive. A negative denominator cannot be repaired by taking a maximum with one. [7.6.2.5, Eqs.7.24-26, PDF 34 / printed 27]
9. **Sway storey.** `beta_s=max[1,1/(1-1.3sum(Nd)/sum(Nk))]`, subject to `sum(Nd)<=0.45sum(Nk)`. Use Cm=1 in the individual beta. The ordinary branch is `Md=max(beta,beta_s)M_end_large`; where the Eq.7.29 condition applies, use `Md=beta*beta_s*M_end_large`. [Eqs.7.27-29, PDF 34 / printed 27]
10. **Biaxial result.** Bind both magnified moments to the same N and combination in one qualified PMM demand vector. [7.6.2.6, PDF 34 / printed 27]

**Eq.7.29 source detail.** In the PDF 34 / printed 27 image, the prose refers to free length while the left side of the printed equation is `lk/i`; the right side is `35/sqrt(Nd/(fck Ac))`. Preserve this source discrepancy through `eq729_length_basis`, recording ln, lk, both ratios and the chosen interpretation. Apply the project's versioned interpretation and report both branches in comparative verification. A conservative comparison may additionally calculate the product branch if either length exceeds the threshold. That is an explicit algorithmic choice, not wording attributed to the standard.

### 5 Beam and column shear

| Operation | Formula and application | Source |
|---|---|---|
| TS 500 diagonal cracking | `Vcr=0.65 fctd bw d (1+gamma Nd/Ac)`. In this equation Nd is a positive magnitude for both tension and compression. Use gamma=0.07 in compression and -0.3 in tension. The gamma=0 branch is permitted under the stated reliable-method condition where web tensile stress is below 0.5 MPa. | TS 500 8.1.3, Eq.8.1, PDF 36 / printed 29 |
| TS 500 shear resistance | `Vr=Vc+Vw`; generally `Vc=0.8Vcr`; `Vw=(Asw/s)fywd d`; require `Vr>=Vd`. Take the effective stirrup-leg area in the relevant direction. | TS 500 8.1.4, Eqs.8.2-5, PDF 37 / printed 30 |
| Minimum shear reinforcement and web limit | `Asw/s>=0.3(fctd/fywd)bw`; `Vd<=0.22fcd bw d`. Require `s<=d/2`, and `s<=d/4` where `Vd>3Vcr`. Bent-up bar contribution is neglected. | TS 500 8.1.5-6, Eqs.8.6-7, PDF 37 / printed 30 |
| Shear-check location | For a direct support, use the section d from the face. For an indirect support or a possible concentrated load within d, use the face. Keep these locations distinct from earthquake capacity-design faces. | TS 500 8.1.2, PDF 36 / printed 29 |
| Column capacity shear | `Ve_cap=(Ma+Mu)/ln`. At a joint meeting SCWB, distribute the connected beams' `sum(Mp)` using the Chapter 4 column end-moment ratios. In the absence of a more exact calculation, beam `Mp≈1.4Mr`. Construct the adverse result in both earthquake senses. The conservative direct-column-capacity branch is also permitted. | TBDY 7.3.7.1-2, Eqs.7.5-6, PDF 139-140 / printed 118-119 |
| Column's own capacity branch | At an end not satisfying SCWB and at the lower foundation end, obtain Ma/Mu from column capacity, with `Mp≈1.4Mr` as the approximation. Use the direction-compatible Nd producing the largest capacity. For a beamless end, establish the physical support/topology basis for this branch; beam absence does not make shear zero. | TBDY 7.3.7.3-4, PDF 141 / printed 120 |
| Column shear bounding | Where gravity plus D-amplified earthquake shear is smaller than capacity shear, that bounding branch may be used. The result cannot be below ordinary design Vd. Build signed combinations before taking the magnitude envelope. Require `Ve<=Vr` and `Ve<=0.85Aw sqrt(fck)`. | TBDY 7.3.7.1 and 7.3.7.5, Eq.7.7, PDF 140-141 / printed 119-120 |
| Zero concrete contribution in a column | In a confinement region, use Vc=0 when both `abs(V_E)` exceeds half the total earthquake-combination shear magnitude and `Nd<=0.05Ac fck`. Define the ratio explicitly for sign reversal/cancellation and use the correct load component. | TBDY 7.3.7.6, PDF 141 / printed 120 |
| Short column | Use the actual short clear length and `1.4Mr` at both ends; confine the whole short length. The applicable condition for fully contacting infill requires transverse reinforcement over the full storey. | TBDY 7.3.8, PDF 141 / printed 120 |
| Beam capacity shear | For the two senses, `Ve=Vdy ±(Mpi+Mpj)/ln`, with `Mpi≈1.4Mri` and `Mpj≈1.4Mrj` as approximations. Where gravity plus D-amplified earthquake shear is smaller, use the specified bounding branch. | TBDY 7.4.5.1, Eq.7.9, PDF 144-145 / printed 123-124 |
| Definition of Vdy | The simply supported beam shear caused by unfactored vertical loads at the beam section. It is not the same field as `factored_Vd`. Derive the support and vertical-load arrangement through a separate record. | TBDY 7.0 symbols, PDF 131 / printed 110 |
| Beam shear limits | `Ve<=Vr` and `Ve<=0.85bw d sqrt(fck)`. In the confinement region, use Vc=0 where earthquake-only shear exceeds half the total earthquake-combination shear. | TBDY 7.4.5.2-3, Eq.7.10, PDF 145 / printed 124 |
| Beam confinement | Extend 2h from the column face at each end. Require phi_t>=8 mm; first stirrup<=50 mm; `s<=min(d/4,8phi_long,min,150 mm)`; transverse leg spacing<=350 mm. The text says d/4 while Figure 7.8 shows hk/4; the earlier recipe adopts the stricter textual requirement explicitly. | TBDY 7.4.4, PDF 144 / printed 123; Figure 7.8, PDF 145 / printed 124 |

Beam longitudinal reinforcement uses `rho>=0.8fctd/fyd`, bar diameter>=12 mm, and at least two continuous bars at both top and bottom throughout the span. The support bottom/top area ratio is at least 0.50 for DTS 1/1a/2/2a and at least 0.30 otherwise. The tensile ratio must not exceed the TS 500 upper limit or 0.02. A beam with `Nd>0.10Ac fck` enters the column-design branch. [TBDY 7.4.1.2 and 7.4.2.1-4, PDF 143 / printed 122]

### 6 SCWB storey alpha and the common joint calculation

#### 6.1 Capacity hierarchy

At each physical joint, for each earthquake direction and both senses, require:

`Mra+Mru>=1.2(Mri+Mrj)`.

Beam moments come from the column-face section and bound actual/selected reinforcement. Column resistance uses the direction-compatible Nd producing the smallest capacity. This axial-force search is the opposite of choosing the maximum Mr for capacity shear. The conditions where both columns have `Nd<=0.10Ac fck`, the single-storey/roof-discontinuation case, and a wall acting as a column about its weak direction produce separate physical-applicability records. [TBDY 7.3.5.1-3, Eq.7.3, PDF 137-139 / printed 116-118]

#### 6.2 Storey alpha procedure

1. Build the physical column population for the storey, direction and earthquake sense. Take both-end SCWB results from the same selected-cage revision.
2. `Vik` is the Chapter 4 directional earthquake shear total for all columns in that storey; `Vis` is the corresponding total for columns satisfying SCWB at both ends. Include low-axial-force columns through the recorded exception permitted by 7.3.6.1. These denominators cannot be built from one target column. [TBDY 7.0 symbols, PDF 131 / printed 110]
3. Calculate `alpha_i=Vis/Vik` and apply the `alpha>=0.70` condition. For `0.70<=alpha<=1`, increase moment and shear by `1/alpha` for columns satisfying the strong-column condition at both ends; design the other columns for their gravity-plus-earthquake demand. Below the threshold, reassess frame ductility classification and system coefficients and repeat the analysis/design cycle. [7.3.6, Eq.7.4, PDF 139 / printed 118]
4. Preserve load decomposition `D=G_part+Q_part+E_part`. If the historical recipe's earthquake-component-only interpretation is selected, use `M*=M_GQ+(1/alpha)M_E` and `V*=V_GQ+(1/alpha)V_E`, retaining the load factors and earthquake signs. This does not automatically apply the same multiplier to N. Scaling the entire total `(GQ+E)/alpha` is a different policy. A final envelope row cannot reconstruct the original E component.

**Source versus interpretation.** Clause 7.3.6.2 directly refers to bending moments and shears; its paragraph does not state “only the E component.” The E-only route above is preserved as a versioned calculation interpretation from the previous recipe. It must not be presented as additional wording in the standard. `LoadTransformationPolicy`, the accepted rule card and example results must identify the same chosen policy. The storey total's sign/envelope aggregation policy must also be explicit. Concurrent directional effects and a sum of independent spectral maxima are different data types.

**Integration distinction.** The additional modal-to-alpha fixture uses an explicitly declared total-M/V feedback policy. That fixture does not silently replace the historical E-only interpretation or determine which branch is implemented in the uninspected local tree. Bind the adopted policy to its actual owner and acceptance evidence.

#### 6.3 Joint shear and enclosure

| Operation | Formula or condition | Source |
|---|---|---|
| Enclosure | Beams frame into all four sides; each beam width is at least three quarters of the connected column width. Determine actual face overlap, direction and continuity from physical topology. | TBDY 7.5.1, PDF 146 / printed 125 |
| Joint shear | `Ve=1.25 fyk(As1+As2)-Vcol`; use As2=0 for a genuinely one-sided beam arrangement. As is the direction-specific tension reinforcement; Vcol is the smaller Chapter 4 column shear above/below the joint. | TBDY 7.5.2.1, Eq.7.11 and Figure 7.10, PDF 146 / printed 125 |
| Resistance | Enclosed: `Ve<=1.7 bj h sqrt(fck)`. Unenclosed: `Ve<=1.0 bj h sqrt(fck)`. Derive bj from Figure 7.10 geometry; it is not universally the column width. | TBDY 7.5.2.2, Eqs.7.12-13, PDF 146-147 / printed 125-126 |
| Joint transverse reinforcement | Enclosed: at least 40% of the amount calculated for confinement of the column below, phi>=8 mm and s<=150 mm. Unenclosed: at least 60%, phi>=8 mm and s<=100 mm. | TBDY 7.5.2.3, PDF 147 / printed 126 |

A joint is one calculation object. All connected beam and column reports show the same `joint_result_id` and the same demand/resistance record. A reinforcement revision invalidates that shared joint result and every affected storey-alpha result.

### 7 Wall calculations on the same pipeline

| Operation | Verified formula or condition | Source |
|---|---|---|
| Definition and axial area | Plan length/thickness>=6. For net Ac, `Ac>=Ndm/(0.35fck)`. For a coupled wall, use the combined wall-segment area and the system Ndm as prescribed. | TBDY 7.6.1.1-2, PDF 147 / printed 126 |
| Thickness | General web `t>=max(h_storey/16,250 mm)` and at least 1/30 of the free branch length. A branch restrained by walls at both ends uses `max(h_storey/20,250 mm)`. If both Eq.7.14 conditions are satisfied, the special wall-system branch is `max(h_storey,max/20,200 mm)`. | TBDY 7.6.1.2-3, PDF 147 / printed 126 |
| Critical region | Boundary regions apply for Hw/lw>2. Printed Eq.7.15 is `max(lw,Hw/6)<=Hcr<=2lw`; prioritizing the prose cap “not exceeding 2lw” gives `Hcr=min[2lw,max(lw,Hw/6)]`. Bind section reduction and rigid-basement start/extension rules to physical levels. | TBDY 7.6.2.1-2, Eq.7.15, PDF 148 / printed 127 |
| Boundary-zone length | Within the critical region, each end `>=max(0.20lw,2t)`; above it `>=max(0.10lw,t)`. If accommodated in another wall branch, establish the equivalent area and extend into the web by `>=max(t,300 mm)`. | TBDY 7.6.2.3-4, PDF 148 / printed 127 |
| Web reinforcement | Sum of both faces in each direction>=0.0025 of the web area; spacing<=250 mm. If Hw/lw<=2, the web covers the whole section. The special Eq.7.14 branch uses 0.002 and spacing<=300 mm. | TBDY 7.6.3.1-2, PDF 148 / printed 127 |
| Crosstie density | Normally at least 4/m² in the web and at least 10/m² in the critical region. Retain the diameter relationship and any resulting increase in count. | TBDY 7.6.3.3, PDF 148-149 / printed 127-128 |
| Boundary longitudinal reinforcement | At each end within the critical height, reinforcement/gross wall area>=0.002; above it>=0.001. At least four phi14 bars at each end. Boundary-zone longitudinal ratio<=0.03, and <=0.06 in laps. Geometry/reinforcement transitions are stepped over three storeys. | TBDY 7.6.5.1, PDF 149 / printed 128 |
| Boundary transverse reinforcement | phi>=8 mm and a<=25phi. In the critical region, provide at least two thirds of the second Eq.7.1 condition; `50<=s<=min(150,6phi_long,t/3)` mm; extend into the foundation by `>=max(300 mm,t)`. Above the critical region, `s<=min(t,200 mm)`. | TBDY 7.6.5.2, PDF 149 / printed 128 |
| Moment envelope | For Hw/lw>2, maintain the base design moment throughout the critical height; above it use the design envelope parallel to the base-to-top line. For Hw/lw<=2, use analysis moments under the applicable branch. | TBDY 7.6.6.1, PDF 151-152 / printed 130-131 |
| Wall capacity hierarchy | For Hw/lw>2, satisfy the Eq.7.3 condition in the strong direction at every storey as prescribed for columns. | TBDY 7.6.6.2, PDF 152 / printed 131 |
| Design shear | For Hw/lw>2, `Ve=beta_v*(Mp,t/Md,t)*Vd`; beta_v=1.5, or 1.0 if reinforced-concrete walls carry all earthquake action. The approximation text states `(Mp)t<=1.25(Mr)t`. Bind the ratio to the specified base section. The alternative gravity-plus-earthquake upper-bounding branch uses 1.2D for uncoupled solid walls and 1.4D for coupled walls. For Hw/lw<=2, use the Chapter 4 analysis branch. | TBDY 7.6.6.3, Eq.7.16, PDF 152 / printed 131 |
| Wall shear resistance | `Vr=Ach(0.65fctd+rho_sh fywd)`; require Ve<=Vr. Uncoupled solid wall `Ve<=0.85Ach sqrt(fck)`; coupled wall `Ve<=0.65Ach sqrt(fck)`. | TBDY 7.6.7.1, Eqs.7.17-18, PDF 152 / printed 131 |
| Construction-joint friction | `Ve<=fctd Ac+mu As fyd`; `Ve<=min[0.2fck Ac,(3.3+0.08fck)Ac]`. Use all relevant web/boundary vertical reinforcement, actual interface condition and physical joint plane. | TBDY 7.6.7.2, Eq.7.19, PDF 152-153 / printed 131-132 |

For these wall calculations, record reduction of shell/pier results to physical wall sections together with openings, coupling beams, boundary zones, storey height and the force resultant. An ETABS pier label alone does not define a physical geometry-and-force section.

### 8 Force transfer to a physical face

The following is a rigid-body equilibrium derivation. It is separate from the TS 500 permission to reduce support moments.

1. Record source section position Os, target physical face Ot, oriented orthonormal axes and both end offsets.
2. Construct the physically signed source vectors `F=(F1,F2,F3)` and `M=(T,M2,M3)`. Explicitly apply the adapter between CSI P and compression-positive section-solver N. A positive-compression scalar N is not automatically physical F1.
3. Let R rotate source components into target axes. Express `r=Os-Ot` in target coordinates.
4. Use `F_t=R F_s` and `M_t=R M_s+r×F_t`. For transfer only along local 1, `M2_t=M2_rot-r1 F3` and `M3_t=M3_rot+r1 F2`. Transverse offsets also retain N-induced moments and any torsion.
5. Where distributed or point loads lie between the sections, include their resultant and moment explicitly in equilibrium. Rigid transfer alone does not produce the force at a differently loaded section.
6. Verify reverse I-to-J orientation, both-direction equilibrium, units and round-trip source/target transfer.

TS 500 6.3.9 / Eq.6.15 permits `DeltaM=V a/3` support-axis moment reduction for continuous flexural members (PDF 27 / printed 20). If `r×F` has already transferred the force to the same face, this permission cannot automatically be treated as another geometric transfer. It requires a separate method field, applicability decision and result.

### 9 Conservative mathematical transfer of spectral demands

CSI's modally combined P/M2/M3 values are not a concurrent vector. The recipe represents them as a component-bound set. Sufficiency established from that set is a separate evidence type. The public CSI response-spectrum-analysis FAQ is identified in the source manifest for this software-semantic distinction.

#### 9.1 Safe enclosure under an affine transformation

Let the six-component source box be `q in [c-r,c+r]`. If unit conversion, axis rotation, face transfer and a fixed-coefficient transformation can be written as `q'=Aq+b`, a safe axis-aligned target box is:

`c'=Ac+b`, `r'=abs(A)r`, `q' in [c'-r',c'+r']`.

This is exact componentwise linear interval arithmetic for the declared independent box. It remains conservative by ignoring unknown component correlations. Rotating only M2/M3 maxima or combining maxima from two source cuts does not replace it. Physical face transfer also needs shear bounds. G/Q and earthquake-direction contributions retain their own intervals, load factors and sign options before combination.

#### 9.2 Nonlinear magnification

Minimum eccentricity, N-dependent beta, moment-sign/capacity branches and a selected-cage revision are nonlinear transformations. Applying T only at the eight source corners does not generally enclose T(box). Use the following declared method:

1. Partition the N interval at tension/compression and method thresholds.
2. On each subinterval, establish admissible Nk, Cm, k, Rm, global magnification and alpha bounds; verify every denominator's domain.
3. For fixed Nk and Cm on the positive-denominator branch where beta is monotone in N, calculate the upper magnification at the upper N bound. If Cm or Nk varies, use a separately justified conservative interval bound or verified optimization.
4. In compression, make each absolute moment bound at least `beta_max*max(M_abs_bound,N_comp,max*emin)`. Include further transformations in their declared order. Associate the resulting enclosure with analytical evidence and tests showing that it contains every T(B).
5. On the resulting three-component design box, use the lower/upper N and moment limits to form eight vertices. Evaluate separately each subbox created by axial-domain branch changes.

#### 9.3 Inference from a box to resistance sufficiency

If the accepted resistance set K for one fixed selected section is convex and all box vertices are in K, the whole box is in K. Verify both K's convexity and that the numerical approximation is a conservative inner approximation. An arbitrary convex hull around sampled capacity points does not establish true resistance-set convexity or sampling safety.

A corner exceedance means that sufficiency has not been established through that conservative box. A physical member failure requires evidence that the failing demand is attainable or another valid failure proof. A successful certified enclosure is reported as set-containment evidence; it is not labelled a concurrent force vector.

### 10 Formula verification records

For each equation retain `rule_id`, `edition`, `clause`, `PDF_page`, `printed_page`, `source_hash`, `physical_applicability`, `input_units`, `sign_convention`, `prerequisites`, `formula_variant`, `result`, `boundary_class` and `evidence`. Numeric limits require separate below-threshold, exact-boundary and above-threshold cases.

The independent hand-calculation and mutation cases include:

- **Minimum eccentricity:** rotate a rectangle by 90 degrees and require the appropriate dimension and moment floor to change. Square-section symmetry alone is insufficient.
- **SCWB and capacity shear:** over the same axial-force range, minimum-capacity selection for SCWB and maximum-capacity selection for capacity shear must produce their distinct expected governing values.
- **Ties:** remove a crosstie while preserving nominal area and require the horizontal-spacing/topology result to change. Check confinement transitions and equality limits.
- **Slenderness:** changes to k, ln, Rm and cage must affect Nk, beta, PMM and the evidence hash as appropriate. Preserve both Eq.7.29 interpretation results.
- **Storey alpha:** deleting one column from the independent storey inventory must expose incomplete denominator coverage. Selecting a target column must not change the complete-storey computation. Compare recombination of signed G/Q/E components with an independent hand calculation.
- **Face transfer:** verify moment change from shear, N-induced moment under a transverse offset, and reversed I/J equilibrium together.
- **Spectral bounds:** in addition to corners, use edge/interior witnesses and synthetic nonlinear transformations whose maxima occur internally. Include cases that expose invalid convexity or sampling assumptions.
- **Reporting:** obtain all versioned inputs/results from one finalized snapshot. Opening a report must not run the formulas again.

#### Previously recorded image checks

The earlier review visually checked TS 500 PDF pp.32-34 for effective length, EI/Nk, beta and Eq.7.29; TBDY PDF p.146 for enclosure equality, bj geometry and the square root in Eq.7.12; and TBDY PDF p.152 for Mp/Md, the approximate Mp inequality and the square root in Eq.7.18. The source-page images resolved square-root signs lost during text extraction. These are retained review references, not newly executed production tests.

### 11 Punching diaphragm and foundation calculations

#### 11.1 TS 500 punching perimeter and eccentricity reduction

1. Construct the loaded area/column/wall face, slab edges, openings, capitals/drop-panel levels and effective depths in both directions. Use `d=(dx+dy)/2`. The punching perimeter up is d/2 outside the loaded area; it is not the column's own perimeter. [TS 500 8.0, PDF 35 / printed 28; 8.3.1, PDF 40 / printed 33]
2. For openings no farther than 5d from the loaded-area edge, remove the perimeter segments between rays tangent from the centroid to the opening edges. Replace a concave loaded boundary by the prescribed tangent-based convex boundary. Where the aspect ratio exceeds three, apply the 3b restriction in Figure 8.4(b). For an edge/corner column evaluate the smaller applicable perimeter from Figure 8.5. With capitals/drop panels, check each critical perimeter separately. [8.3.1, PDF 41-43 / printed 34-36]
3. Vpd is the algebraic sum of all forces normal to the slab within the perimeter. For a slab include the difference between upper/lower column forces and the internal slab load. For a foundation include column force and the integrated soil reaction inside the perimeter. Total column Nd is not automatically Vpd. [8.3.1, PDF 40 / printed 33]
4. `Vpr=gamma fctd up d`; require `Vpr>=Vpd`. Use gamma=1 for centric axial loading. For eccentricity, select the applicable physical-geometry method below. [Eqs.8.20-25, PDF 40-41 / printed 33-34]

| Geometry or clause | Equation | Applicability |
|---|---|---|
| General Eqs.8.22-23 | `gamma=1/[1+eta (e/Wm) up d]`; `eta=1/[1+sqrt(b2/b1)]` | `b2>=0.7b1`. b1 is parallel to eccentricity and b2 perpendicular; use the smallest rectangle enclosing up. Wm is the section modulus of the area inside the perimeter, not a different method's perimeter polar/second-moment quantity. |
| Interior rectangular column/loaded area, Eq.8.24 | `gamma=1/[1+1.5(ex+ey)/sqrt(bx by)]` | Excludes slab-edge/corner cases. bx and by are dimensions of the punching perimeter. |
| Interior circular column/loaded area, Eq.8.25 | `gamma=1/[1+2e/(d+d0)]` | d0 is the circular load/column diameter. |

Construct eccentricity from 40% of the slab moment sum in the relevant plane and the upper/lower axial-force difference, using the oriented equilibrium of Figure 8.3: `e=0.4(Md1+Md2)/(N2-N1)`. Use the relevant eccentricity magnitude after converting raw local signs to physical equilibrium. If N2-N1 approaches zero, do not clamp the ratio numerically to obtain a passing result; use an applicable perimeter-shear method that transfers moment directly. [TS 500 8.3.1, PDF 41 / printed 34]

The general reinforced-punching method in TS 500 8.3.2 requires an experimentally validated reinforcement/profile/steel arrangement, slab thickness>=250 mm, and resistance no greater than 1.5 times the unreinforced resistance (PDF 42 / printed 35). TS 500 10.4.2 excludes reinforcement contribution in the punching check for a continuous flat foundation (PDF 54 / printed 47). Keep the special TBDY seismic reinforced-punching route under a separate method identity. Do not create a hybrid capacity by mixing coefficients from different methods.

#### 11.2 TBDY 7.11 punching and moment transfer

**Finite-element route.** Under vertical loads together with D-amplified earthquake effects, obtain shear per unit width vpd at d/2 from the face. Require `tau_pd=vpd/d<=fctd`. Finite-element averaging must not hide an extreme mesh point or opposite sides of a discontinuous section. Record recovery/sampling rules and mesh convergence. [TBDY 7.11.7, Eq.7.27, PDF 159 / printed 138]

**Moment-sharing route.** Determine the physically signed total moment balancing the upper/lower column moments at the joint. Transfer `gamma_f M` through flexural reinforcement and `(1-gamma_f)M` through the punching perimeter. For a rectangular perimeter, `gamma_f=1/[1+(2/3)sqrt(b1/b2)]`, where b1 is the perimeter dimension parallel to loading and b2 perpendicular. For a circle, gamma_f=0.60. [TBDY 7.11.8-9, Eq.7.28, PDF 160 / printed 139]

Implement the d-thick perimeter stress field as `tau(x,y)=a+b x+c y`, solving its three coefficients from total-force and two-moment equilibrium. Include the actual edge, corner and opening geometry in the integrals and search every perimeter segment for maximum stress. Check equilibrium with the `(1-gamma_f)` moments and report `tau_pd=max(abs(tau))`. The signs follow the same `r×F` convention. Do not superimpose TS 500 gamma capacity reduction and TBDY gamma_f moment sharing; use the selected method's complete compatible demand/resistance pair.

**Reinforcement route.** For h>=250 mm, uniformly distributed crossties/chairs use `tau_pr=0.5fctd+rho fyd<=1.5fctd`; shear studs use `tau_pr=0.75fctd+rho fyd<=1.75fctd`. Clause 7.11.10 also requires a reinforcement contribution of at least fctd. Provide at least 4/m²; first reinforcement from the face<=d/4; spacing between reinforcement<=d/2. [TBDY 7.11.10-11, Eq.7.29, PDF 160 / printed 139]

For strip stirrups or stud rails, replace rho by `Awp/(up s)`. Provide at least two perpendicular directions; first reinforcement<=d/4; spacing normal to the face<=d/2; spacing parallel to the face<=2d. Check the perimeter outside the reinforced region separately and retain the chosen TS 500/TBDY method scope. [TBDY 7.11.12, Eq.7.30, PDF 160-161 / printed 139-140]

The preceding visual review checked eta and the rectangular gamma square roots on TS 500 PDF p.41, and gamma_f on TBDY PDF p.160. Three different symbols must remain separate domain fields: TS 500 gamma for axial influence on shear, TS 500 gamma for punching resistance reduction, and TBDY gamma_f for moment transfer.

#### 11.3 Diaphragm collectors and slab to wall connection

Under TBDY 7.11.3, apply D to in-plane earthquake stresses obtained from the elastic diaphragm. If tensile stress exceeds fctd, use reinforcement remaining after flexural requirements to satisfy `sigma_t<=rho fyd`. Require `sigma_c<=0.85fcd` in compression. In each shear direction require `tau<=0.65fctd+rho fyd` and `tau<=0.65sqrt(fck)`. The same full reinforcement area cannot be consumed both by flexural capacity and by in-plane capacity. [Eq.7.25, PDF 158 / printed 137]

For slab-to-wall shear transfer, `tau_r=mu rho fyd`; the specific monolithic-interface value in this clause is mu=1.0. Derive transfer force from the difference between the wall's D Vd shears above and below the floor. The total resistance expression is `2Asa fyd+mu Asb fyd`. Check anchorage, available residual reinforcement area and shear-friction transfer along collectors. [TBDY 7.11.3-5, Eq.7.26, PDF 158-159 / printed 137-138]

#### 11.4 Concrete to concrete or steel shear friction

TS 500 8.1.7 uses `Vr=Awf fyd mu`. Awf includes only reinforcement perpendicular to the interface and adequately anchored on both sides. The general table values of mu are 1.4 for monolithic concrete; 1.0 for old-to-new concrete roughened by at least 5 mm; 0.6 for an unroughened concrete interface; and 0.7 for steel-to-concrete. The static branch for an inclined bar acting in tension is `Vr=Awf fyd(mu sin(alpha_f)+cos(alpha_f))`. An inclined bar in compression does not contribute to that resistance. Under earthquake action, reinforcement is arranged perpendicular to the crack plane. [Eqs.8.8-9 and Table 8.1, PDF 38 / printed 31]

The upper limit is `Vd<=0.2fcd Ac`, using fcd no greater than 25 MPa in that limit. Provide separately anchored reinforcement for direct tension. Where the lowest reliable sustained compression is established, apply the specified reduction branch. The special wall-foundation-joint expression `fctd Ac+mu As fyd` in TBDY 7.6.7.2 and its different upper limits are not automatically added to the general TS 500 expressions. Applicability selects the complete special method. [TS 500 8.1.7, PDF 38 / printed 31; TBDY 7.6.7.2, PDF 152-153 / printed 131-132]

#### 11.5 Establishing the superstructure to foundation demand

1. Establish the foundation/superstructure force-transfer plane, rigid-basement classification and start of the wall critical height.
2. Where critical wall height starts at the foundation top, including the no-basement branch, magnify the wall foundation overturning moment by `D_upper`. For a high-ductility wall, its base yield moment is the upper bound. Wall shear comes from 7.6.6.3.
3. In the same branch, derive other wall components and non-wall member internal forces as `0.6D_upper` times the ductile-design internal forces.
4. Where the critical wall height starts above the foundation top in the rigid-basement branch, obtain all foundation transfers through the lower-building method in 4.10.1.5. [TBDY 4.10.3.1-2, PDF 80 / printed 59]
5. Combine gravity contributions and the earthquake combinations of 4.4.4 into the same physically signed foundation-demand vector. Apply each required design moment/shear magnification once in the source ledger. [TBDY 16.7.3.1, PDF 368 / printed 347]

A foundation reaction file does not by itself define every geotechnical or section-design demand. Derive demands through the transfer method for each direction and signed combination. The result contract is `FoundationDemandSet`: N, Vx, Vy, Mx, My, Mz, reference plane, units, load combination, transfer method and `source_run_id`.

#### 11.6 Geotechnical calculation and soil contact

| Operation | Formula or condition | Source |
|---|---|---|
| Design principle | For each failure mechanism, `Et<=Rt`, with `Rt=Rk/gamma_R`. Bearing resistance and permitted displacement are separate checks. Address overall stability and interaction near slopes, landslides, excavations or tunnels. | TBDY 16.7.1-4, PDF 367-368 / printed 346-347 |
| Resistance factors | Shallow foundation: vertical 1.4, friction 1.1, passive 1.4. | TBDY 16.8.2 and Table 16.2, PDF 369 / printed 348 |
| Contact pressure | For every static and earthquake case, `q0<=qt`, with `qt=qk/gamma_Rv`. Obtain q0 from a contact solution for the same demand vector. | TBDY 16.8.3.1, Eqs.16.6-7, PDF 369 / printed 348 |
| Bearing resistance | `qk=c Nc sc dc ic gc bc + q Nq sq dq iq gq bq +0.5 gamma B' Ngamma sgamma dgamma igamma ggamma bgamma`. `Nq=exp(pi tan(phi')) tan²(45°+phi'/2)`; `Nc=(Nq-1)cot(phi')`; `Ngamma=2(Nq-1)tan(phi')`. | TBDY 16.8.3.2, Eq.16.8, PDF 369 / printed 348 |
| Factors and strata | Take shape, depth, load-inclination, ground-slope and base-inclination factors consistently from one identified, generally accepted geotechnical method. Do not default every factor to one. Include variable strata/discontinuities within the influence depth. | TBDY 16.8.3.2-3, PDF 369 / printed 348 |
| Horizontal sliding | `Vth<=Rth+0.3Rpt`. Drained `Rth=Ptv tan(delta)/1.1`; undrained `Rth=Ac cu/1.1`; `Rpt=Rpk/1.4`. Here Ac is the actual contact area in compression. | TBDY 16.8.4.1-5, Eqs.16.9-12, PDF 370 / printed 349 |
| Friction upper values | Unless established otherwise by tests, tan(delta): cast-in-place concrete/compacted soil 0.6; precast concrete/soil 0.4; cast-in-place concrete/concrete 0.5; concrete/bedrock 0.5. For earthquake friction of foundations below groundwater, use the prescribed undrained resistance. | TBDY 16.8.4.3,6 and Table 16.3, PDF 370-371 / printed 349-350 |
| Settlement and permanent deformation | Include cyclic pore-pressure changes, strength/stiffness loss and displacement. The nonlinear permanent-deformation requirement applies to high-rise buildings on soils other than ZA/ZB, and other DTS 1/1a/2/2a buildings on soils other than ZA/ZB/ZC. | TBDY 16.8.3.4, PDF 369-370 / printed 348-349 |

**Contact solution.** Where rigid full contact is valid, derive base pressure from N and both moment-equilibrium equations and evaluate the four corners and other critical points. If tension occurs, solve a compression-only contact polygon rather than allowing soil tension. Verify `integral(q dA)=N` and that the two first-moment integrals reproduce Mx/My. In a spring-supported raft branch, retain model area, spring units, compression-only behaviour, soil layering and mesh convergence. If the bearing method uses effective B'/L' for eccentricity, distinguish its effective area from the contact-pressure solution area. Groundwater and uplift alter Ptv and effective weights. Use the smallest reliable compression in the same combination when deriving sliding resistance.

#### 11.7 Reinforced concrete foundation and tie beam design

TS 500 10.1 generally requires cover>=50 mm. Keep soil/settlement demand roles and reinforced-concrete section-strength demand roles separate when sizing the foundation. Apply TBDY Chapter 16 resistance and combinations for earthquake geotechnical design. [TS 500 PDF 52 / printed 45; TBDY 16.7.3, PDF 368 / printed 347]

For an isolated foundation, the minimum plan dimension is 0.70 m, area>=1.0 m² and thickness>=max(250 mm,cantilever projection/4). The critical section for moment and one-way shear is the column face; punching uses the d/2 perimeter. Check bending, shear, punching and anchorage in both directions separately. The tensile reinforcement ratio in each direction is at least 0.002 and spacing at most 250 mm. [TS 500 10.3.2-3, PDF 53-54 / printed 46-47]

For a continuous foundation with beams, beam depth>=clear span/10 and slab thickness>=200 mm. A continuous flat foundation/raft slab is at least 300 mm thick. Check column-face shear and punching, provide compression-zone reinforcement of at least one third of the tension reinforcement, and evaluate shear-friction transfer at horizontal construction joints. Superstructure/foundation/soil stiffness interaction determines reaction distribution. [TS 500 10.4.2-3, PDF 54 / printed 47]

TBDY tie beams run in two directions between isolated footings/pile caps, and along column/wall lines in continuous foundations. The ZA-soil exception may apply. `Nb=0.10 SDS Nk`, where this Nk is the largest axial force of the connected column/wall, not Euler Nk. Tension is carried by reinforcement; compression and, where applicable, buckling are evaluated together. Minimum section 300×300 mm; rho>=0.005; phi8 ties at s<=200 mm. A slab used instead is at least 150 mm thick and must demonstrate equivalent force transfer. [TBDY 16.8.5, Eq.16.13, PDF 371 / printed 350]

Verification examples for this module include interior/edge/corner punching; an opening at the 5d limit; two critical capital perimeters; increased shear on one side due to moment transfer; N2-N1 approaching zero; removal of tensile raft contact; sliding under water uplift; the 0.3 passive-resistance limit; 0.6D foundation transfer and the wall-yield-moment cap; and separate complete TS 500/TBDY reinforced-punching method records. Verify global force/moment balance, geometry and the normative result separately in each example.


## Appendix C — Golden examples and adapter contracts


This appendix is generated from GOLDEN_CASES.json. It retains 73 primary check examples and 12 separate adapter contract examples. The 333 assertions are independent example arithmetic and data contracts. They are separate from the existing 44 production comparisons and from any other 333-record project scope. Formula text is display-only; the static independent verifier never reads it as an expression.

The local integration checkout at a2e26b664d9b2b217e828de2c1df0c3df26068b1 plus unfinished changes is NOT_INSPECTED. Published context is pinned to b255c3030c09c88a17bbec766fc2bb22682ad027. Production-owner comparison, recorded-source replay, live ETABS validation and engineering acceptance remain NOT_RUN unless a separate current verification record states otherwise.

### GE-SRC-001 — Integrity and change detection for the three-model package

**Check:** SRC-001 · **Kind:** CONTRACT_FIXTURE · **Population:** PRIMARY_CHECK_EXAMPLE

Source-file integrity and the independently expected inventory.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

- **GE-S01**, TBDY_PDF_Golden_V2_Manifest.json; SHA-256 `1de835eae29246546cb6ece6255663757c9c00ab82358bcd8fe4f0d4bb2c8914`. Manifest fields pages, numeric_cases_total and source_pdf_sha256. Original PDF pages: null; atlas pages: null. Source-document inventory and page total

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| pdf_page_counts | [197, 258, 261] | page | V2 manifest and original PDF files |
| document_count | 3 | document | documents table |
| reference_record_count | 467 | record | reference_cases table |

#### Calculation and intermediate results

GE-SRC-001-S01: **Reconcile the page population.**

Formula (display only): `p=p2+p3+p4`

Substitution: `197+258+261`

Result: 716 pages (units: page)

GE-SRC-001-S02: **Bind each file by its complete SHA-256.**

Formula (display only): `SHA256(file)=manifest.sha256`

Substitution: `Recomputed digest of each source file`

Result: All three source digests are recorded in the source manifest (units: digest)

GE-SRC-001-S03: **Detect a one-byte change.**

Formula (display only): `SHA256(abc) != SHA256(abd)`

Substitution: `Replace UTF-8 abc with abd`

Result: Modified content cannot retain the same source identity (units: bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| total_pdf_pages | 716 | page | Expected result of the declared example |
| document_count | 3 | document | Expected result of the declared example |
| reference_record_count | 467 | record | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-SRC-001-A01 | Page total | 716 | page | 1e-09 | 0 |
| GE-SRC-001-A02 | SHA-256 known answer | ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad | digest | 0 | 0 |
| GE-SRC-001-A03 | One-byte change | true | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-SRC-001-A02 |
| negative | SPECIFIED_EXECUTABLE | GE-SRC-001-A03 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Changing one byte must fail the digest comparison. Equal page counts do not prove equal content.

**Report mapping:** Manifest to document identity and digest, then physical PDF page and case reference. The 467 reference records and 73 check headings are separate populations.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `b9762344e679875b68f6fd7e53b053d6ebbc9b8cc5ff0f315d30da6168c03f1f`

**Case SHA-256:** `e946154cd0eb4adfe6e364863abb7a3a210b29f3d9cc9a087349f70405a6e03f`

### GE-SRC-002 — Model identity and dimensional unit conversion

**Check:** SRC-002 · **Kind:** CONTRACT_FIXTURE · **Population:** PRIMARY_CHECK_EXAMPLE

Transfer one source row to the kernel with explicit units.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. PDF page 186, printed page 184, SZ01 major-axis moment magnification. Original PDF pages: [186]; atlas pages: [11]. Nd = 471.11 kN, lk = 5.23 m and a 30 cm section

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| Nd | 471.11 | kN | 2.pdf page 186, SZ01 major-axis row |
| lk | 5.23 | m | The same source row |
| b_h | [30, 30] | cm | PDF2 column section |

#### Calculation and intermediate results

GE-SRC-002-S01: **Convert force.**

Formula (display only): `N=N_kN*1000`

Substitution: `471.11*1000`

Result: 471110 N (units: N)

GE-SRC-002-S02: **Convert length and area.**

Formula (display only): `lk_mm=1000lk_m; Ac_mm2=100b_cm*h_cm`

Substitution: `5.23*1000; 30*30*100`

Result: 5230 mm and 90000 mm² (units: mm; mm²)

GE-SRC-002-S03: **Carry model identity.**

Formula (display only): `source_model_id=consumer_model_id`

Substitution: `Two-storey 30 cm model and three-storey 40 cm model`

Result: The two-storey 30 cm and three-storey 40 cm models are distinct records (units: identifier)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| core_Nd | 471110 | N | Expected result of the declared example |
| core_lk | 5230 | mm | Expected result of the declared example |
| core_Ac | 90000 | mm² | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-SRC-002-A01 | Force conversion | 471110 | N | 1e-09 | 0 |
| GE-SRC-002-A02 | Length conversion | 5230 | mm | 1e-09 | 0 |
| GE-SRC-002-A03 | Area conversion | 90000 | mm² | 1e-09 | 0 |
| GE-SRC-002-A04 | Distinct model identities | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-SRC-002-A04 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** A value of 5.23 m labelled 5.23 mm violates the source unit contract. Do not silently repair it from its magnitude.

**Report mapping:** Source Nd and lk become dimensional quantities in N and mm while retaining the same model identity. The compression-positive PDF value does not establish the CSI P sign convention.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `416a4d1748ba452a6c59e42da5c0574d801d034665445caf10f8474159dfa52f`

**Case SHA-256:** `baf3ba4851832fa547e093cb48e57a54e1860afa2b57155c79e33d058dcdf446`

### GE-SRC-003 — Force coverage on both sides of an internal joint

**Check:** SRC-003 · **Kind:** CONTRACT_FIXTURE · **Population:** PRIMARY_CHECK_EXAMPLE

An independently prescribed cut population for a 3 m column formed by two analysis elements.

**Normative or contract basis:** Source and adapter contract; PMM v6 cut-side identity

#### Source trace

- **GE-S03**, PIPELINE_UNIFICATION_20261115.md; SHA-256 `177ce572ab06d9705569e744dcd9e40684bf35d88a568e1d6b9e8f7c76a6a36d`. PMM v6 multi-element column cut coverage; the 3 m geometry is a declared fixture. Original PDF pages: null; atlas pages: null. Element-side identity contract; the 3 m geometry is an explicitly selected benchmark

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| element_chain | ["E1:I=0,J=1.5", "E2:I=1.5,J=3.0"] | m | Selected verification geometry |
| combinations | ["DX", "DY"] | identifier | Selected design group |
| cut_sides | ["E1/I: ObjSta0,ElmSta0", "E1/J: ObjSta1.5,ElmSta1.5", "E2/I: ObjSta1.5,ElmSta0", "E2/J: ObjSta3,ElmSta1.5"] | CutKey | Three configured positions including both analysis-element sides of the internal joint |

**Frozen contract data:**

```json
{
  "expected_keys": [
    [
      "C-DEMO",
      "DX",
      "E1/I",
      0,
      0
    ],
    [
      "C-DEMO",
      "DX",
      "E1/J",
      1.5,
      1.5
    ],
    [
      "C-DEMO",
      "DX",
      "E2/I",
      1.5,
      0
    ],
    [
      "C-DEMO",
      "DX",
      "E2/J",
      3,
      1.5
    ],
    [
      "C-DEMO",
      "DY",
      "E1/I",
      0,
      0
    ],
    [
      "C-DEMO",
      "DY",
      "E1/J",
      1.5,
      1.5
    ],
    [
      "C-DEMO",
      "DY",
      "E2/I",
      1.5,
      0
    ],
    [
      "C-DEMO",
      "DY",
      "E2/J",
      3,
      1.5
    ]
  ],
  "observed_missing": [
    [
      "C-DEMO",
      "DX",
      "E1/I",
      0,
      0
    ],
    [
      "C-DEMO",
      "DX",
      "E1/J",
      1.5,
      1.5
    ],
    [
      "C-DEMO",
      "DX",
      "E2/I",
      1.5,
      0
    ],
    [
      "C-DEMO",
      "DX",
      "E2/J",
      3,
      1.5
    ],
    [
      "C-DEMO",
      "DY",
      "E1/I",
      0,
      0
    ],
    [
      "C-DEMO",
      "DY",
      "E1/J",
      1.5,
      1.5
    ],
    [
      "C-DEMO",
      "DY",
      "E2/J",
      3,
      1.5
    ]
  ],
  "observed_duplicate": [
    [
      "C-DEMO",
      "DX",
      "E1/I",
      0,
      0
    ],
    [
      "C-DEMO",
      "DX",
      "E1/J",
      1.5,
      1.5
    ],
    [
      "C-DEMO",
      "DX",
      "E2/I",
      1.5,
      0
    ],
    [
      "C-DEMO",
      "DX",
      "E2/J",
      3,
      1.5
    ],
    [
      "C-DEMO",
      "DY",
      "E1/I",
      0,
      0
    ],
    [
      "C-DEMO",
      "DY",
      "E1/J",
      1.5,
      1.5
    ],
    [
      "C-DEMO",
      "DY",
      "E2/J",
      3,
      1.5
    ],
    [
      "C-DEMO",
      "DY",
      "E1/J",
      1.5,
      1.5
    ]
  ]
}
```

#### Calculation and intermediate results

GE-SRC-003-S01: **Count element sides per combination.**

Formula (display only): `ncut=2*2`

Substitution: `E1 I/J and E2 I/J`

Result: Four records: E1/J has ObjSta 1.5 and ElmSta 1.5; E2/I has ObjSta 1.5 and ElmSta 0 (units: record; m)

GE-SRC-003-S02: **Construct the expected population.**

Formula (display only): `nexpected=ncombo*ncut`

Substitution: `2*4`

Result: Eight records (units: record)

GE-SRC-003-S03: **Identify the missing DY E2 I-side row.**

Formula (display only): `coverage=nobserved/nexpected`

Substitution: `7/8`

Result: Coverage is 0.875 (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| expected_record_count | 8 | record | Expected result of the declared example |
| observed_count_in_incomplete_fixture | 7 | record | Expected result of the declared example |
| coverage_ratio | 0.875 | ratio | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-SRC-003-A01 | Expected complete CutKey population | 8 | record | 1e-09 | 0 |
| GE-SRC-003-A02 | Missing-row coverage | 0.875 | 1 | 1e-09 | 0 |
| GE-SRC-003-A03 | Duplicate restores only the raw count | 8 | record | 1e-09 | 0 |
| GE-SRC-003-A04 | Duplicate does not restore CutKey equality | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-SRC-003-A04 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | SPECIFIED_EXECUTABLE | GE-SRC-003-A02, GE-SRC-003-A04 |

**Narrative variant:** Duplicating E1/J instead of supplying E2/I gives eight rows but fails exact set and uniqueness comparisons.

**Report mapping:** Compare the expected CutKey set against observed rows and report each missing side. Object station 1.5 m carries two distinct analysis-element sides.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `22627dbbed26967a3e2d0e73eff2f79e93afed6e28ff73946c4924d3d72e7dda`

**Case SHA-256:** `9566ca8207a39da891543b4f1dee8657e2baba4dc82764dc6a790bd7f19de3e7`

### GE-SRC-004 — Analysis generation after a PDelta change

**Check:** SRC-004 · **Kind:** CONTRACT_FIXTURE · **Population:** PRIMARY_CHECK_EXAMPLE

Prevent old forces from being relabelled as results of a revised analysis setup.

**Normative or contract basis:** Source and immutable-run contract

#### Source trace

- **GE-S03**, PIPELINE_UNIFICATION_20261115.md; SHA-256 `177ce572ab06d9705569e744dcd9e40684bf35d88a568e1d6b9e8f7c76a6a36d`. Source snapshot and immutable run records; generations 7 and 8 are fixture values. Original PDF pages: null; atlas pages: null. Source and generation binding; generations 7 and 8 are selected fixture values

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| model_id | M-DEMO | identifier | Contract fixture |
| previous_generation | 7 | generation | Initial recorded generation |
| pdelta_revisions | ["PDELTA-A", "PDELTA-B"] | revision | Changed initial loading state |
| new_generation | 8 | generation | New analysis record |

**Frozen contract data:**

```json
{
  "target": {
    "model_id": "M-DEMO",
    "generation": 8,
    "pdelta_revision": "PDELTA-B"
  },
  "old_force": {
    "model_id": "M-DEMO",
    "generation": 7,
    "pdelta_revision": "PDELTA-A"
  },
  "new_force": {
    "model_id": "M-DEMO",
    "generation": 8,
    "pdelta_revision": "PDELTA-B"
  }
}
```

#### Calculation and intermediate results

GE-SRC-004-S01: **Separate the old force record.**

Formula (display only): `force.generation=request.generation`

Substitution: `7==8`

Result: The old record does not match (units: bool)

GE-SRC-004-S02: **Bind the newly analysed force record.**

Formula (display only): `force.generation=request.generation`

Substitution: `8==8`

Result: The new record matches (units: bool)

GE-SRC-004-S03: **Preserve the archive.**

Formula (display only): `archive.generation=7`

Substitution: `New run 8, old run 7`

Result: Two immutable source records remain (units: generation)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| old_force_matches | false | bool | Expected result of the declared example |
| new_force_matches | true | bool | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-SRC-004-A01 | Old force does not match target | false | bool | 0 | 0 |
| GE-SRC-004-A02 | New force matches target | true | bool | 0 | 0 |

**Tolerance rationale:** Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-SRC-004-A02 |
| negative | SPECIFIED_EXECUTABLE | GE-SRC-004-A01 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | SPECIFIED_EXECUTABLE | GE-SRC-004-A01 |

**Narrative variant:** Replacing the generation label 7 with 8 does not prove that analysis ran. An unchanged case name does not replace a generation identity.

**Report mapping:** Model preparation, changed initial stiffness or loading, new analysis and convergence evidence, generation 8 forces and RunResult 8 form one lineage.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `76cd61a77cce716f5699b26e0f85f9eb4cb088ce754e7793587f6282b28e8cbd`

**Case SHA-256:** `2de066c3aa2cf8c7b189116584039e602becc522d49820ffc2cd7d918867b9c7`

### GE-SRC-005 — ComboBook and signed force replay

**Check:** SRC-005 · **Kind:** CONTRACT_FIXTURE · **Population:** PRIMARY_CHECK_EXAMPLE

Linear combination of vectors from the same cut under an explicitly selected approximate vertical-earthquake branch.

**Normative or contract basis:** TBDY 2018 4.4.2.1 Eq. 4.9, 4.4.3.2 Eq. 4.10 and 4.4.4.1 Eq. 4.11; reinforced-concrete strength design with S=H=0, excluding members requiring the special vertical analysis of 4.4.3.1

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. PDF page 1, project SDS only; the forces are independently selected benchmark inputs. Original PDF pages: [1]; atlas pages: [13]. SDS only; the force values are not taken from this report

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| SDS | 0.508151 | g/g | EX6 page 1 |
| G_N_M2_M3 | [1000, 20, 30] | kN;kNm;kNm | Selected signed benchmark |
| Q_N_M2_M3 | [300, 10, 5] | kN;kNm;kNm | Selected signed benchmark |
| EX_N_M2_M3 | [40, 200, 80] | kN;kNm;kNm | Selected signed benchmark |
| EY_N_M2_M3 | [30, 40, 180] | kN;kNm;kNm | Selected signed benchmark |
| S_H | 0 | load | Explicit zero-load assumption |

#### Calculation and intermediate results

GE-SRC-005-S01: **Calculate the G coefficient.**

Formula (display only): `cG=1+0.3*(2/3)*SDS`

Substitution: `1+0.2*0.508151`

Result: 1.1016302 (units: 1)

GE-SRC-005-S02: **Sum the axial force.**

Formula (display only): `N=cG*NG+NQ+NEX+0.3NEY`

Substitution: `1.1016302*1000+300+40+0.3*30`

Result: 1450.6302 kN (units: kN)

GE-SRC-005-S03: **Calculate both moments from the same source vectors.**

Formula (display only): `M2 = cG*M2G + M2Q + M2EX + 0.3M2EY; apply the same rule to M3`

Substitution: `1.1016302*20+10+200+0.3*40; 1.1016302*30+5+80+0.3*180`

Result: M2 = 244.032604 kN·m and M3 = 172.048906 kN·m (units: kNm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| cG | 1.1016302 | coefficient | Expected result of the declared example |
| N | 1450.6302 | kN | Expected result of the declared example |
| M2 | 244.032604 | kNm | Expected result of the declared example |
| M3 | 172.048906 | kNm | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-SRC-005-A01 | Gravity coefficient | 1.1016302 | 1 | 1e-09 | 0 |
| GE-SRC-005-A02 | Axial force replay | 1450.6302 | kN | 1e-09 | 0 |
| GE-SRC-005-A03 | Local 2 moment replay | 244.032604 | kN·m | 1e-09 | 0 |
| GE-SRC-005-A04 | Local 3 moment replay | 172.048906 | kN·m | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Using EY coefficient 0.4 gives N = 1453.6302 kN, M2 = 248.032604 kN·m and M3 = 190.048906 kN·m. This violates the intended 30 percent definition and must fail the ComboBook comparison. A component envelope cannot replace the signed input vector.

**Report mapping:** EX6 supplies SDS only. Explicit benchmark vectors pass through ComboAST coefficients, the same CutKey and the same initial state to produce a design demand. These forces are not EX6 building results.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `a704e58f6f88bd48ca9eef78e933a8d01e892ece13ecde05c31b8b68e81b5eb0`

**Case SHA-256:** `1b8ab710eccf35389aa14a17ca4fa2ca851042a1c76f3d145fc498912c0a4294`

### GE-CHK-001 — Lower concrete-strength bound for C30

**Check:** CHK-001 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

The C25 lower bound for concrete used in a new reinforced-concrete building.

**Normative or contract basis:** TBDY 2018 7.2.5.1; standard PDF page 133, printed page 112

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. PDF page 7, printed page equal to PDF page minus 2; C30 for columns, beams and slabs. Original PDF pages: [7]; atlas pages: [5]. C30 columns, beams and slabs with fck = 30 MPa

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| fck | 30 | MPa | Material table on 2.pdf page 7 |
| fck_min | 25 | MPa | TBDY 7.2.5.1 |

#### Calculation and intermediate results

GE-CHK-001-S01: **Compare the assigned C30 class with its characteristic strength.**

Formula (display only): `fck ≥ fck_min`

Substitution: `30 ≥ 25`

Result: Condition true with a 5 MPa strength margin (units: MPa; bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| minimum_strength_margin | 5 | MPa | Independent arithmetic recalculation |
| minimum_strength_satisfied | true | bool | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-001-A01 | Strength margin | 5 | MPa | 1e-09 | 0 |
| GE-CHK-001-A02 | Lower bound | true | bool | 0 | 0 |
| GE-CHK-001-A03 | Derived C24 rejection | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-001-A02 |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-001-A03 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** C25 satisfies equality; the derived fck = 24 MPa input fails the lower bound.

**Report mapping:** Source C30 becomes fck = 30 MPa, compared with 25 MPa, and the material result remains linked to the assigned members.

**Qualification:** This compares a reported material class with the code threshold; it is not a laboratory material acceptance.

**Frozen input SHA-256:** `0f634e36a247bae1929c90fbc28b8479395d23ddd442f9b2a8bcf2a1dd9d9047`

**Case SHA-256:** `4b3d312f49e6336dd43554b2b9fce4e1032644c529caacc76c8410dbf4ffc456`

### GE-CHK-002 — Concrete-class range for the selected method

**Check:** CHK-002 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

The C25 to C80 concrete-class range of TBDY Chapter 7.

**Normative or contract basis:** TBDY 2018 7.1.3 and 7.2.5.3(a); standard PDF pages 132 to 133

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. PDF page 7; assigned concrete class C30. Original PDF pages: [7]; atlas pages: [5]. Assigned C30 material grade

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| fck | 30 | MPa | 2.pdf page 7 |
| class_lower_bound | 25 | MPa | TBDY 7.2.5.3(a) |
| class_upper_bound | 80 | MPa | TBDY 7.1.3 |

#### Calculation and intermediate results

GE-CHK-002-S01: **Evaluate both bounds on the same characteristic strength.**

Formula (display only): `25 ≤ fck ≤ 80`

Substitution: `25 ≤ 30 ≤ 80`

Result: Within range, with a 50 MPa margin to the upper bound (units: MPa; bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| upper_strength_margin | 50 | MPa | Independent arithmetic recalculation |
| within_tbdy_chapter_7_range | true | bool | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-002-A01 | Class interval | true | bool | 0 | 0 |
| GE-CHK-002-A02 | Upper-bound margin | 50 | MPa | 1e-09 | 0 |
| GE-CHK-002-A03 | Derived C90 exclusion | false | bool | 0 | 0 |

**Tolerance rationale:** Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance. Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-002-A01 |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-002-A03 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** C80 satisfies upper-bound equality. C90 lies outside this Chapter 7 class range.

**Report mapping:** Source C30 defines the method applicability range. TS 500 stress-block parameters also retain their own tabulated applicability limits.

**Qualification:** Class applicability does not establish that every constitutive model is unconditionally valid up to C80.

**Frozen input SHA-256:** `84c23982ccd32b128ca0466ce618221794ba5b549fd80bca705ea62b49f51f74`

**Case SHA-256:** `32a8471526d5b434ad900d1ac8bd9d3631ae7c05e74de61f510ee0076aa4a843`

### GE-CHK-003 — Dimensions of the 300 mm square column

**Check:** CHK-003 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

The 300 mm minimum side for a rectangular column.

**Normative or contract basis:** TBDY 2018 7.3.1.1; standard PDF page 135, printed page 114

#### Source trace

- **GE-S05**, col1.docx; SHA-256 `75e14b85d28958e13b59e77cf12242ef6bf2546492754cd33ac9b900e45fc0de`. Column Reinforcement Design, S1 (D-4), Storey 1 (30/30), first three tables. Original PDF pages: null; atlas pages: null. 30 by 30 cm section, C25/S420, governing combination 16 and four Phi18 bars

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| b | 300 | mm | col1.docx S1 30/30 section |
| h | 300 | mm | col1.docx S1 30/30 section |

#### Calculation and intermediate results

GE-CHK-003-S01: **Convert centimetres to millimetres and select the smaller side.**

Formula (display only): `b_min=min(b, h)`

Substitution: `min(300, 300)`

Result: 300 mm; equality satisfies the dimensional bound (units: mm; bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| b_min | 300 | mm | Independent arithmetic recalculation |
| geometry_condition_satisfied | true | bool | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-003-A01 | Smaller side | 300 | mm | 1e-09 | 0 |
| GE-CHK-003-A02 | Equality at dimensional limit | true | bool | 0 | 0 |
| GE-CHK-003-A03 | Derived 299 mm rejection | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-003-A02 |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-003-A03 |
| boundary | SPECIFIED_EXECUTABLE | GE-CHK-003-A02 |
| missing_source | OPEN | None |

**Narrative variant:** A derived 299 by 300 mm section fails. The circular-section branch uses a 350 mm diameter bound, not the rectangular 300 mm side bound.

**Report mapping:** The 30/30 cm heading maps to a 300/300 mm section and then its minimum side.

**Qualification:** This geometric example is shape-specific and separate from capacity and detailing checks.

**Frozen input SHA-256:** `14573d6f408f814d06262edcb5ecb7678cf6620c487fa9f6da88c495b185d4a3`

**Case SHA-256:** `056276bd59eda856c543f09c1a03ebf4c3a2de8c98b3b8ee3a4e83b9decc47e0`

### GE-CHK-004 — Seismic axial compression limit

**Check:** CHK-004 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

The seismic axial-demand limit for a 300 by 300 mm C30 column with normalized compression sign.

**Normative or contract basis:** TBDY 2018 7.3.1.2

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. PDF pages 7 and 191; ZEMIN KAT SZ03 row with Ndm = -848.33 and Nd = -1114.48 kN. Original PDF pages: [7, 191]; atlas pages: [5, 12]. C30; the ZEMIN KAT SZ03 axial-force row with Ndm = -848.33 and Nd = -1114.48 kN

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| b_h | [300, 300] | mm | Source section and 1080 kN limit on page 191 |
| fck | 30 | MPa | 2.pdf material table on page 7 |
| native_P | -848.33 | kN | Same page 191 SZ03 row, G+Q-Ey-0.3Ex+0.3Ez |

#### Calculation and intermediate results

GE-CHK-004-S01: **Calculate gross area.**

Formula (display only): `Ac=b h`

Substitution: `300×300`

Result: Ac = 90000 mm² (units: mm²)

GE-CHK-004-S02: **Normalize compression and calculate the limit.**

Formula (display only): `Ndm=−P; Nlim=0.40fckAc`

Substitution: `Ndm=848.33; 0.40×30×90000/1000`

Result: Ndm = 848.33 kN and Nlim = 1080 kN (units: kN)

GE-CHK-004-S03: **Compare the demand with its separate axial bound.**

Formula (display only): `u=Ndm/Nlim`

Substitution: `848.33/1080`

Result: Utilization = 0.785490741, within the bound (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Nlim | 1080 | kN | Printed 1080.00 on PDF page 191, matching the recalculation |
| u_axial_seismic | 0.7854907407407408 | 1 | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-004-A01 | Seismic axial limit | 1080 | kN | 1e-09 | 0 |
| GE-CHK-004-A02 | Seismic axial utilization | 0.7854907407407408 | 1 | 1e-09 | 0 |
| GE-CHK-004-A03 | Derived tensile input gives zero compression | 0 | kN | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Ndm = 1080 kN is equality and 1080.1 kN exceeds the limit. If native P = +200 kN denotes tension, do not turn it into a 200 kN compression demand by taking the absolute value.

**Report mapping:** Use the same source row for seismic combination, Ndm and 0.4 Ac fck. Distinguish repeated SZ03 labels by their source row; do not invent Unique IDs.

**Qualification:** This independently reproduces the limit for the printed loading state; it does not verify the PMM surface or complete cut population.

**Frozen input SHA-256:** `73b3f68e861c4ada7284d38ff60128622fa021fed487bb32d96949c67b8f9618`

**Case SHA-256:** `ed5c0dd71274933b5b4827740b13bd305ebc295040dfb8bf93a50f8be74aeafc`

### GE-CHK-005 — TS 500 axial compression limit

**Check:** CHK-005 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

The 0.90 fcd Ac limit for the same source section under 1.4G + 1.6Q.

**Normative or contract basis:** TS 500 2000 7.4.1 Eq. 7.7

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. PDF pages 7 and 191; same ZEMIN KAT SZ03 row as GE-CHK-004. Original PDF pages: [7, 191]; atlas pages: [5, 12]. C30; the ZEMIN KAT SZ03 axial-force row with Ndm = -848.33 and Nd = -1114.48 kN

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| Ac | 90000 | mm² | Source 300 by 300 mm section |
| fck | 30 | MPa | 2.pdf page 7 |
| gamma_c | 1.5 | 1 | TS 500 design-strength coefficient |
| Nd | 1114.48 | kN | Same page 191 SZ03 row, native force -1114.48 kN |

#### Calculation and intermediate results

GE-CHK-005-S01: **Calculate concrete design strength.**

Formula (display only): `fcd=fck/gamma_c`

Substitution: `30/1.5`

Result: fcd = 20 MPa (units: MPa)

GE-CHK-005-S02: **Calculate the axial limit.**

Formula (display only): `Nlim=0.90fcdAc`

Substitution: `0.90×20×90000/1000`

Result: Nlim = 1620 kN (units: kN)

GE-CHK-005-S03: **Calculate utilization.**

Formula (display only): `u=Nd/Nlim`

Substitution: `1114.48/1620`

Result: Utilization = 0.687950617, within the bound (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| fcd | 20 | MPa | Independent arithmetic recalculation |
| Nlim | 1620 | kN | Printed 1620.00 on PDF page 191 |
| u_axial_ts500 | 0.6879506172839507 | 1 | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-005-A01 | Concrete design strength | 20 | MPa | 1e-09 | 0 |
| GE-CHK-005-A02 | TS 500 axial limit | 1620 | kN | 1e-09 | 0 |
| GE-CHK-005-A03 | Axial utilization | 0.6879506172839507 | 1 | 1e-09 | 0 |
| GE-CHK-005-A04 | Derived limit exceedance | true | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-005-A04 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Nd = 1620 kN is equality and 1620.1 kN exceeds the limit. A change to gamma_c updates both fcd and the limit in the same record.

**Report mapping:** The page 191 gravity combination, Nd and 0.9 Ac fcd produce their own TS 500 result. Keep this result distinct from CHK-004.

**Qualification:** Do not add reinforcement contribution to this bound. The raw axial capacity of a PMM section is a different quantity.

**Frozen input SHA-256:** `0f2387b24e516594ebdb0ad2a15c2e2642e6dd4df1450bf2668e7a05445b390f`

**Case SHA-256:** `a1761338253c320e6743a9ebc8f2dde0a74ec679857905a14dd1fd38097640d4`

### GE-CHK-006 — Modal mass completeness in both directions

**Check:** CHK-006 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

The 95 percent cumulative participation and retention of modes whose individual contribution exceeds 3 percent.

**Normative or contract basis:** TBDY 2018 4.8.1.2 and Eq. 4.30

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. PDF pages 21 and 22; upper Modal table on page 22 with incremental and cumulative Ux and Uy. Original PDF pages: [21, 22]; atlas pages: [8, 9]. Modal case; incremental Ux/Uy and cumulative Ux/Uy in the upper table on PDF page 22

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| UX | [0, 0.92566, 0, 0.07434, 0, 0] | 1 | Upper Modal table, page 22 |
| UY | [0.92566, 0, 0, 0, 0.07434, 0] | 1 | Same modal case and table |
| required_cumulative_ratio | 0.95 | 1 | TBDY 4.8.1.2 |

#### Calculation and intermediate results

GE-CHK-006-S01: **Sum individual modal contributions in each direction.**

Formula (display only): `sum(UX), sum(UY)`

Substitution: `0.92566+0.07434; 0.92566+0.07434`

Result: X = 1.00000 and Y = 1.00000 (units: 1)

GE-CHK-006-S02: **Find the first sufficient mode count for both directions.**

Formula (display only): `YM=max(YMx, YMy)`

Substitution: `YMx=4, YMy=5`

Result: YMx = 4 and YMy = 5, requiring the first 5 modes in 3D; the source retains 6 (units: mode)

GE-CHK-006-S03: **Retain substantial individual modal contributions.**

Formula (display only): `r_mode>0.03`

Substitution: `0.07434>0.03`

Result: The fourth and fifth modes, each with contribution 0.07434, cannot be omitted (units: mode; 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| sum_ux | 1 | 1 | PDF page 22, cumulative Ux = 1.00000 |
| sum_uy | 1 | 1 | PDF page 22, cumulative Uy = 1.00000 |
| YM_xy_min | 5 | mode | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-006-A01 | Cumulative UX | 1 | 1 | 1e-09 | 0 |
| GE-CHK-006-A02 | Cumulative UY | 1 | 1 | 1e-09 | 0 |
| GE-CHK-006-A03 | First four Y modes are insufficient | true | bool | 0 | 0 |
| GE-CHK-006-A04 | First-four-mode Y total | 0.92566 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-006-A03 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | SPECIFIED_EXECUTABLE | GE-CHK-006-A03 |

**Narrative variant:** Using only the first four modes gives X = 1.00 and Y = 0.92566. Sufficiency in X does not establish sufficiency in Y.

**Report mapping:** Incremental contributions from the upper Modal table produce cumulative totals and directional mode-count requirements. Do not mix rows from the lower Modal-prime table.

**Qualification:** This recomputes the published participation table for one case and does not prove another modal case complete.

**Frozen input SHA-256:** `571c6e1c7a8a079f4b5f6b789e66f46cf22269b864ffe9c535708559cbd16c03`

**Case SHA-256:** `d4dde71698d4f3db827f89fa311c0498874ccc18ce38d5ed23a174cf790ee63c`

### GE-CHK-007 — Reported PMM demand and the first reinforcement candidate

**Check:** CHK-007 · **Kind:** SOURCE_REPORTED · **Population:** PRIMARY_CHECK_EXAMPLE

Transfer the same end-force vector and 4Phi18 candidate for S1, Storey 1, combination 16.

**Normative or contract basis:** TS 500 section equilibrium and strain compatibility; TBDY 2018 7.3.2

#### Source trace

- **GE-S05**, col1.docx; SHA-256 `75e14b85d28958e13b59e77cf12242ef6bf2546492754cd33ac9b900e45fc0de`. Column Reinforcement Design, S1 (D-4), Storey 1 (30/30), first three tables. Original PDF pages: null; atlas pages: null. 30 by 30 cm section, C25/S420, governing combination 16 and four Phi18 bars

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| reported_N | 7.43 | source t | First combination table No. 16, NBot |
| reported_M11 | 2.39 | source t*m | Same row No. 16, M1Bot |
| reported_M22 | 1.03 | source t*m | Same row No. 16, M2Bot |
| reported_required_As | 9.0 | cm² | First design summary, one-percent minimum |
| bars | 4Φ18 | count/diameter | First design summary |
| reported_minimum_moments | [0.18, 0.18] | source t*m | First design summary |

#### Calculation and intermediate results

GE-CHK-007-S01: **Keep the force vector at the same physical end together.**

Formula (display only): `D=(N, M11, M22)`

Substitution: `D=(7.430, 2.39, 1.03)`

Result: Combination 16 carries D = (7.430, 2.39, 1.03) with one source row identity (units: source t; source t*m)

GE-CHK-007-S02: **Compare each reported moment with the reported minimum.**

Formula (display only): `Mdesign=max(|M|, Mmin)`

Substitution: `max(2.39, .18); max(1.03, .18)`

Result: Design moment magnitudes are 2.39 and 1.03 in the source moment unit (units: source t*m)

GE-CHK-007-S03: **Recalculate candidate steel area.**

Formula (display only): `As=4 pi18²/4`

Substitution: `1017.8760 mm² /100`

Result: As = 10.178760 cm², rounding to 10.18; provided over minimum area = 1.130973 (units: cm²)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| As_candidate | 10.17876019763093 | cm² | Report prints 10.18; area arithmetic reproduced |
| reported_critical_combo | 16 | identifier | Printed in the source |
| reported_neutral_axis_depth | 7.5 | cm | Source heading S1/storey 1 |
| reported_neutral_axis_angle | 12.28 | degree | Source heading S1/storey 1 |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-007-A01 | Candidate steel area | 10.17876019763093 | cm² | 1e-09 | 0 |
| GE-CHK-007-A02 | M11 demand selection | 2.39 | source t·m | 1e-09 | 0 |
| GE-CHK-007-A03 | M22 demand selection | 1.03 | source t·m | 1e-09 | 0 |
| GE-CHK-007-A04 | Derived minimum moment governing | 0.18 | source t·m | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_EXECUTABLE | GE-CHK-007-A04 |
| missing_source | OPEN | None |

**Narrative variant:** With M11 changed to 0.10, the same reported minimum governs at 0.18. Combining another combination maximum N with these two moments destroys the same-vector example.

**Report mapping:** No. 16 NBot, M1Bot and M2Bot form one end demand with a recorded minimum and candidate identity. Source M11 and M22 require an explicit axis map before becoming CSI M2 and M3. GE-CHK-120 supplies a separate section-kernel benchmark.

**Qualification:** The source reports the PMM design. Only demand selection and candidate area are recomputed here; no independent PMM utilization is produced. GE-CHK-120 uses a different section and cannot stand in for COL1 S1 capacity. Resolve the source t unit before converting to kN.

**Frozen input SHA-256:** `e295701391b34f8bcc88aaca8959397404e6395da5ebdd1097d5348cfd5c3741`

**Case SHA-256:** `73e1dc7d5b79fd0ddc7c8610c25e6932ab19f088e1990ea9f962190e1841653f`

### GE-CHK-009 — Longitudinal ratio of four 18 mm bars

**Check:** CHK-009 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

The 4Phi18 longitudinal ratio of a 300 by 300 mm column, retaining template and concrete candidate roles.

**Normative or contract basis:** TBDY 2018 7.3.2.1

#### Source trace

- **GE-S05**, col1.docx; SHA-256 `75e14b85d28958e13b59e77cf12242ef6bf2546492754cd33ac9b900e45fc0de`. col1.docx, S1 (D-4), Storey 1 (30/30), first three tables. Original PDF pages: null; atlas pages: null. 30 by 30 cm section, C25/S420, governing combination 16 and four Phi18 bars

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| Ac | 90000 | mm² | COL1 S1 Storey 1 |
| bar_count | 4 | count | 4Phi18 |
| bar_diameter | 18 | mm | 4Phi18 |
| rho_min | 0.01 | 1 | TBDY 7.3.2.1 |
| rho_max | 0.04 | 1 | Normal column region; lap-splice branch is separate |

#### Calculation and intermediate results

GE-CHK-009-S01: **Calculate area from the actual bars.**

Formula (display only): `As=n pi phi²/4`

Substitution: `4×pi×18²/4`

Result: As = 1017.876020 mm² (units: mm²)

GE-CHK-009-S02: **Divide by gross section area.**

Formula (display only): `rho=As/Ac`

Substitution: `1017.876020/90000`

Result: rho = 0.011309734, or 1.130973 percent (units: 1; percent)

GE-CHK-009-S03: **Apply the ratio limits to the candidate role.**

Formula (display only): `0.01≤rho≤0.04`

Substitution: `0.01≤0.011309734≤0.04`

Result: The ratio limits are satisfied, consistent with the reported 1.13 percent (units: bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| As | 1017.8760197630929 | mm² | Independent arithmetic recalculation |
| rho_percent | 1.1309733552923256 | % | Source prints 1.13 percent; rounding difference retained |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-009-A01 | Steel area | 1017.8760197630929 | mm² | 1e-09 | 0 |
| GE-CHK-009-A02 | Steel ratio in percent | 1.1309733552923256 | % | 1e-09 | 0 |
| GE-CHK-009-A03 | Derived four-16-mm-bar ratio | 0.008936085770210968 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Four 16 mm bars give As = 804.2477 mm² and rho = 0.89361 percent, below the candidate minimum. A TEMPLATE cannot replace the selected reinforcement.

**Report mapping:** The reported As(Sup) = 10.18 cm² and 4Phi18 define bars, area and ratio for a candidate result. An ETABS TEMPLATE ratio is not an approved installed-cage result.

**Qualification:** PMM, spacing and splice checks must consume the same cage as this longitudinal-ratio check.

**Frozen input SHA-256:** `d49476fd311f0278aee672fc204be5529ea5d1ff396fb7c7a0da1f44a22b034c`

**Case SHA-256:** `69fc8c71868b5d1f3eafc06496e332abbf1c3e9bc7857b5bee5fd68d4e23523f`

### GE-CHK-010 — From source drift ratio to dimensional storey displacement

**Check:** CHK-010 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Multiply a dimensionless source drift by height exactly once to obtain reduced relative displacement.

**Normative or contract basis:** TBDY 2018 4.9.1.1 and the source-field dimensional contract

#### Source trace

- **GE-S06**, 07_GORELI_KAT_OTELEME_KONTROLU.xlsx; SHA-256 `0ec41c2ac49dda5c1ce818f1a282f3212283c0d7e3bf24689925b21b9b5381e4`. DATA!A4:E4 and DRIFT_KONTROL!D10; +4.50 storey, h = 4.5 m. Original PDF pages: null; atlas pages: null. Storey +4.50, height 4.5 m and raw X drift 0.001741536505615905; effective ratio uses R/I = 7

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| drift_ratio | 0.001741536505615905 | 1 | DATA!D4 |
| storey_height | 4500 | mm | DATA!B4 = 4.5 m |
| R_over_I | 7 | 1 | Source effective-drift relation |

#### Calculation and intermediate results

GE-CHK-010-S01: **Convert the ratio to dimensional displacement.**

Formula (display only): `Delta=drift_ratio hi`

Substitution: `.001741536505615905×4500`

Result: Delta = 7.836914275 mm (units: mm)

GE-CHK-010-S02: **Calculate effective drift ratio separately.**

Formula (display only): `delta/hi=(R/I) drift_ratio`

Substitution: `7×.001741536505615905`

Result: Effective drift ratio = 0.0121907555393113, matching DRIFT_KONTROL!D10 (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Delta_mm | 7.836914275271572 | mm | Independent arithmetic recalculation |
| effective_drift_ratio | 0.012190755539311334 | 1 | Source cell D10 |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-010-A01 | Dimensional drift | 7.836914275271572 | mm | 1e-09 | 0 |
| GE-CHK-010-A02 | Effective drift ratio | 0.012190755539311334 | 1 | 1e-09 | 0 |
| GE-CHK-010-A03 | Derived changed storey height | 0.002612304758423857 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** At the same 7.836914275 mm displacement, h = 3000 mm gives ratio 0.002612304758. A physical-height revision changes the result.

**Report mapping:** DATA!D4 becomes dimensional Delta using height, then a separately identified effective ratio using R/I, and supplies CHK-105. Do not divide the original ratio by height a second time.

**Qualification:** The source-field conversion is recomputed. Independent top and bottom joint displacements are not provided, so their difference is not independently reconstructed.

**Frozen input SHA-256:** `6c386c01f39304cef49829e5be3c422e3448e73c9320a2e7d085021b7789c51b`

**Case SHA-256:** `a982b2a5a1bd4fd70b8ea45822740679e8e17f933f011413f1e4241e43f47fba`

### GE-CHK-011 — Design-spectrum corner periods and sample ordinates

**Check:** CHK-011 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

The four horizontal elastic-spectrum branches and reduced spectrum at a selected period.

**Normative or contract basis:** TBDY 2018 2.3.4 Eqs. 2.2 to 2.3, 4.2.1 Eq. 4.1 and 4.4.1 Eq. 4.8

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. PDF pages 6 and 20; SDS, SD1, TA, TB and S(T) table. Original PDF pages: [6, 20]; atlas pages: [4, 7]. SDS = 0.6592, SD1 = 0.1912, TA = 0.058, TB = 0.290 and the S(T) table

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| SDS | 0.6592 | coefficient in g | 2.pdf page 6 |
| SD1 | 0.1912 | coefficient in g*s | 2.pdf page 6 |
| TL | 6 | s | TBDY 2.3.4 transition to constant displacement |
| R_D_I | [8, 3, 1] | 1 | 2.pdf page 6 |
| T | 0.4 | s | Sample period on page 20 |

#### Calculation and intermediate results

GE-CHK-011-S01: **Calculate the corner periods.**

Formula (display only): `TA=.2SD1/SDS; TB=SD1/SDS`

Substitution: `.2×.1912/.6592; .1912/.6592`

Result: TA = 0.058009709 s and TB = 0.290048544 s (units: s)

GE-CHK-011-S02: **Calculate sample elastic ordinates.**

Formula (display only): `Sae(0)=.4SDS; Sae(.1)=SDS; Sae(.4)=SD1/.4`

Substitution: `Sae(0)=.26368; Sae(.1)=.6592; Sae(.4)=.478`

Result: Sae(0) = 0.26368, Sae(0.1) = 0.6592 and Sae(0.4) = 0.478; printed as 0.26, 0.66 and 0.48 (units: coefficient in g)

GE-CHK-011-S03: **Apply the reduction factor for the selected branch.**

Formula (display only): `For T > TB, Ra = R/I and SaR = Sae/Ra`

Substitution: `Ra=8; SaR(.4)=.478/8`

Result: Ra = 8 and SaR(0.4) = 0.05975 g; multiply by g to obtain physical acceleration (units: coefficient in g)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| TA | 0.05800970873786408 | s | Independent arithmetic recalculation |
| TB | 0.29004854368932037 | s | Independent arithmetic recalculation |
| Sae_0p4 | 0.478 | coefficient in g | Printed 0.48 on PDF page 20 |
| SaR_0p4 | 0.05975 | coefficient in g | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-011-A01 | TA | 0.05800970873786408 | s | 1e-09 | 0 |
| GE-CHK-011-A02 | TB | 0.29004854368932037 | s | 1e-09 | 0 |
| GE-CHK-011-A03 | Elastic spectrum at 0.4 s | 0.478 | g coefficient | 1e-09 | 0 |
| GE-CHK-011-A04 | Reduced spectrum at 0.4 s | 0.05975 | g coefficient | 1e-09 | 0 |
| GE-CHK-011-A05 | Derived long-period branch | 0.007966666666666667 | g coefficient | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** At T = TB, SDS = SD1/TB. Both adjacent branches give 0.031866667 at T = 6 s; at T = 12 s, SD1 TL/T² = 0.007966667.

**Report mapping:** SDS and SD1 determine TA and TB, the elastic coefficients and Ra-reduced coefficients. Keep normalized coefficients distinct from m/s².

**Qualification:** This reproduces source spectrum parameters with the stated equations; it does not claim that every native ETABS function point was captured.

**Frozen input SHA-256:** `f96e9f9ecb05782b14dcd422c38fe5336a20376969f2c79f3fe73f7bac8a7ee6`

**Case SHA-256:** `5c3dc5b5dde656db8c0f907c149c36630563043f55c0b63a49564d5356e98db5`

### GE-CHK-101 — Seismic weight from storey loads

**Check:** CHK-101 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

G + nQ weights for the two source storeys using n = 0.30.

**Normative or contract basis:** TBDY 2018 4.5.9 and Table 4.3

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. PDF pages 19 and 20; G, Q, n and storey weights; printed total W = 2968.78 kN. Original PDF pages: [19, 20]; atlas pages: [6, 7]. G, Q, n and storey weights; printed total W = 2968.78 kN

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| storey_G | [1466.62, 1396.12] | kN | Page 19 upper and ground storeys |
| storey_Q | [176.72, 176.72] | kN | Page 19 |
| participation_n | 0.3 | 1 | Page 19 hykk field |
| gravity_acceleration | 9.80665 | m/s² | Explicit value used only for equivalent-mass conversion |

#### Calculation and intermediate results

GE-CHK-101-S01: **Calculate G plus nQ for each storey.**

Formula (display only): `wi=Gi+nQi`

Substitution: `1466.62+.30×176.72; 1396.12+.30×176.72`

Result: 1519.636 kN and 1449.136 kN (units: kN)

GE-CHK-101-S02: **Sum storey weights.**

Formula (display only): `W=sum(wi)`

Substitution: `1519.636+1449.136`

Result: 2968.772 kN, differing by 0.008 kN from the printed 2968.78 (units: kN)

GE-CHK-101-S03: **Convert weight to its associated mass.**

Formula (display only): `m=W/g`

Substitution: `2968.772/9.80665`

Result: 302.730494 tonnes (units: tonne)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| w1 | 1519.636 | kN | Printed 1519.64 on PDF page 19 |
| w0 | 1449.136 | kN | Printed 1449.14 on PDF page 19 |
| W | 2968.772 | kN | Independent arithmetic recalculation |
| m_from_W | 302.730494103491 | ton | Derived using the explicitly selected gravitational acceleration |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-101-A01 | Upper-storey weight | 1519.636 | kN | 1e-09 | 0 |
| GE-CHK-101-A02 | Lower-storey weight | 1449.136 | kN | 1e-09 | 0 |
| GE-CHK-101-A03 | Comparison with printed total | 2968.78 | kN | 0.015 | 0 |
| GE-CHK-101-A04 | Mass derived from weight | 302.730494103491 | tonne | 1e-09 | 0 |
| GE-CHK-101-A05 | Derived n equals 0.60 | 3074.804 | kN | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. The printed total is 2968.78 kN; arithmetic on the printed G and Q values gives 2968.772 kN. The retained 0.015 kN allowance covers the 0.008 kN printed-input discrepancy. This does not relax an engineering acceptance limit.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** With n = 0.60 the weight becomes 3074.804 kN. Changing n revises both storey weights and the total. Adding self-weight a second time breaks reconciliation.

**Report mapping:** The G, Q and hykk columns produce wi, W and an explicit W/g conversion. The 297.67 t free-mass field on page 20 remains a separate source quantity.

**Qualification:** G+nQ is reproduced within printed rounding. W/g = 302.730494 t differs from the reported free mass 297.67 t; this is not a complete native mass-source reconciliation.

**Frozen input SHA-256:** `6211fce09b3625ffdfcc3720829e640b504fa54f40d99bfc19dbaad245cffb48`

**Case SHA-256:** `c6b57d922cd6d21bd107ff1e78c29196ee5e997fbab5ae9b996baf86fb6f70f6`

### GE-CHK-102 — Directional modal period and method-specific period

**Check:** CHK-102 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Separate natural modal periods from the period cap used by the equivalent-lateral-force method.

**Normative or contract basis:** TBDY 2018 4.7.3.2 to 4.7.3.4 and 4.8.1

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. PDF pages 20 to 22; mode 1 in Y, mode 2 in X, T = 1.24879 s and f = 0.80077 Hz. Original PDF pages: [20, 21, 22]; atlas pages: [7, 8, 9]. Modal1 Y and Modal2 X; T = 1.24879 s, frequency 0.80077 Hz, Hn = 10 m, Ct = 0.1, TpA = 0.56 and Tp = 0.79

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| modal_period | 1.24879 | s | Page 21, modes 1 and 2 |
| frequency | 0.80077 | Hz | Same modal rows |
| building_height | 10 | m | Page 20 |
| Ct | 0.1 | s/m^(3/4) | Page 20 |
| period_multiplier | 1.4 | 1 | TBDY 4.7.3.2 |

#### Calculation and intermediate results

GE-CHK-102-S01: **Check frequency and period consistency.**

Formula (display only): `T=1/f`

Substitution: `1/.80077`

Result: 1/f = 1.248798032 s; the printed period is 1.24879 s, a difference of about 8.0e-6 s (units: s)

GE-CHK-102-S02: **Identify direction using modal participation.**

Formula (display only): `Y→mod1; X→mod2`

Substitution: `PDF 22 Uy1=.92566; Ux2=.92566`

Result: Both directions have Tmodal = 1.24879 s; mode 1 carries Uy = 0.92566 and mode 2 Ux = 0.92566; retain distinct mode identities (units: s; mode; 1)

GE-CHK-102-S03: **Calculate the equivalent-load period cap.**

Formula (display only): `TpA=Ct Hn^.75; Tp=min(Tmodal, 1.4TpA)`

Substitution: `.1×10^.75=.562341325; min(1.24879, .787277855)`

Result: TpA = 0.562341325 s and Tp = 0.787277855 s, rounding to 0.79 s (units: s)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| T_from_f | 1.2487980318943017 | s | Independent arithmetic recalculation |
| TpA | 0.5623413251903492 | s | Independent arithmetic recalculation |
| Tp_for_equivalent_load | 0.7872778552664886 | s | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-102-A01 | Reciprocal frequency comparison | 1.24879 | s | 2e-05 | 0 |
| GE-CHK-102-A02 | Empirical period | 0.5623413251903492 | s | 1e-09 | 0 |
| GE-CHK-102-A03 | Method period | 0.7872778552664886 | s | 1e-09 | 0 |
| GE-CHK-102-A04 | Derived shorter modal period | 0.7 | s | 1e-09 | 0 |

**Tolerance rationale:** The frequency is printed to five decimals and the period to five decimals. Inverting 0.80077 gives 1.248798032 s against 1.24879 s; 0.00002 s covers their independent rounding. This does not relax an engineering acceptance limit. Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** For Tmodal = 0.70 s, Tp remains 0.70 s. The period cap is not applied to the displacement calculation under 4.9.1.1.

**Report mapping:** The frequency-period table and directional participation identify the natural T; the method-specific Tp is a separate field and does not overwrite modal T.

**Qualification:** This is arithmetic period selection and capping, not a rerun of the modal eigensolution or convergence assessment.

**Frozen input SHA-256:** `20adc0d34d82af7255ff5f8f6d8dc88338ad95c700bae39703b233b4f5c6d441`

**Case SHA-256:** `53839990137cd81d433e9d67eae9600990542692aa1374ad3681d580216a94dd`

### GE-CHK-103 — Base shear and storey force distribution

**Check:** CHK-103 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

A complete small example of the equivalent-load period cap, minimum base shear and force distribution.

**Normative or contract basis:** TBDY 2018 4.7.1 to 4.7.3, Eqs. 4.19, 4.22 and 4.23

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. PDF pages 6, 19 and 20; spectrum parameters, storey weights, VtE = 90.13 kN and roof addition 1.35 kN. Original PDF pages: [6, 19, 20]; atlas pages: [4, 6, 7]. SDS, SD1, R, I, Hn, Ct, storey weights, VtE = 90.13 kN and roof addition 1.35 kN

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| W | 2968.78 | kN | Page 20 |
| SDS_SD1 | [0.6592, 0.1912] | coefficients in g | Page 6 |
| R_I | [8, 1] | 1 | Page 6 |
| Hn_Ct | [10, 0.1] | m and s/m^0.75 | Page 20 |
| storey_weights | [1449.14, 1519.64] | kN | Page 19 ground and upper storeys |
| storey_elevations | [5, 10] | m | Page 19 |
| storey_count | 2 | storey | Page 6 |

#### Calculation and intermediate results

GE-CHK-103-S01: **Calculate method period and reduced spectrum.**

Formula (display only): `Tp=1.4CtHn^.75; SaR/g=SD1/(Tp R/I)`

Substitution: `Tp=.787277855; SaR/g=.1912/(.787277855×8)`

Result: Tp = 0.787277855 s and SaR/g = 0.03035776993 (units: 1; s)

GE-CHK-103-S02: **Compare spectral and minimum base shear.**

Formula (display only): `V=max(W SaR/g, .04W I SDS)`

Substitution: `max(90.125540208, 78.280791040)`

Result: max(90.125540208, 78.280791040) = 90.125540208 kN, rounding to 90.13 kN (units: kN)

GE-CHK-103-S03: **Distribute the rounded reported base shear.**

Formula (display only): `DeltaFN=.0075NV; Fi=(V−DeltaFN)wiHi/sum(wjHj)`

Substitution: `DeltaFN=1.35195; sum(wH)=22442.10`

Result: Roof addition = 1.35195 kN; sum(wH) = 22442.10; ground force = 28.663053675 kN and roof total = 61.466946325 kN; combined force = 90.13 kN (units: kN; kN*m)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| V_spectral | 90.1255402083964 | kN | Independent arithmetic recalculation |
| V_min | 78.28079104 | kN | Independent arithmetic recalculation |
| VtE_report | 90.13 | kN | Printed on PDF page 20 |
| Delta_FN | 1.35195 | kN | Derived using printed VtE; PDF page 20 gives 1.35 |
| F_ground_equivalent | 28.66305367523538 | kN | Derived value distributed to storeys |
| F_roof_total_equivalent | 61.4669463247646 | kN | Derived including the roof addition |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-103-A01 | Printed base-shear target | 90.13 | kN | 0.006 | 0 |
| GE-CHK-103-A02 | Minimum base shear | 78.28079104 | kN | 1e-09 | 0 |
| GE-CHK-103-A03 | Roof additional force | 1.35195 | kN | 1e-09 | 0 |
| GE-CHK-103-A04 | Ground-storey allocation | 28.66305367523538 | kN | 1e-09 | 0 |
| GE-CHK-103-A05 | Distribution equilibrium | 90.13 | kN | 1e-09 | 0 |
| GE-CHK-103-A06 | Derived minimum governs | 78.28079104 | kN | 1e-09 | 0 |

**Tolerance rationale:** The 90.13 kN source result is printed to two decimals. The 0.006 kN allowance retains the original rounded-target comparison. This does not relax an engineering acceptance limit. Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** For SaR/g = 0.02, the spectral force is 59.3756 kN and the 78.28079104 kN minimum governs. Distributed forces must sum to the revised VtE.

**Report mapping:** Source parameters determine Tp and VtE; wiHi determines the independently derived equivalent-load distribution. The source modal forces 36.67 and 16.46 kN are a different result family.

**Qualification:** VtE and the roof addition match printed rounding. The equivalent force distribution is derived from the code equation and is not compared against the source modal Fi column.

**Frozen input SHA-256:** `d8dcb02011700b4425fcee52d04699fc9daa86bd150e0253793c103442f8fc46`

**Case SHA-256:** `e3e439db52c49e8489b063df2cfd5841d0cfa28878b81daafbbb82d57ab25114`

### GE-CHK-104 — Scaling modal base shear

**Check:** CHK-104 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Force amplification for the source-declared gammaE = 0.80 branch.

**Normative or contract basis:** TBDY 2018 4.8.4.1 Eq. 4.31; displacement consumer under 4.9.1.1 remains separate

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. PDF page 20; VtE = 90.13 kN, Vmodal = 53.13 kN, gammaE = 0.80, force factor 1.36 and displacement factor 1.00. Original PDF pages: [20]; atlas pages: [7]. VtE = 90.13 kN, modal shear 53.13 kN, gammaE = 0.80, printed force scale 1.36 and displacement scale 1.00

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| equivalent_base_shear | 90.13 | kN | Page 20, X direction |
| modal_base_shear | 53.13 | kN | Page 20, X direction |
| gammaE | 0.8 | 1 | Source-declared branch on page 20 |

#### Calculation and intermediate results

GE-CHK-104-S01: **Calculate the required base force.**

Formula (display only): `Vtarget=gammaE VtE`

Substitution: `.8×90.13`

Result: Target = 72.104 kN (units: kN)

GE-CHK-104-S02: **Calculate an amplification factor no smaller than one.**

Formula (display only): `beta=max(1, Vtarget/Vmodal)`

Substitution: `max(1, 72.104/53.13)`

Result: beta = 1.357124035, rounding to 1.36 (units: 1)

GE-CHK-104-S03: **Calculate the scaled force.**

Formula (display only): `V_after=beta Vmodal`

Substitution: `1.357124035×53.13`

Result: Scaled force = 72.104 kN (units: kN)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| beta_force | 1.3571240353849048 | 1 | Target 1.36 on PDF page 20 |
| V_after | 72.104 | kN | Independent arithmetic recalculation |
| beta_displacement_report | 1.0 | 1 | Separately printed field on PDF page 20; not derived by this calculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-104-A01 | Printed amplification target | 1.36 | 1 | 0.006 | 0 |
| GE-CHK-104-A02 | Scaled base shear | 72.104 | kN | 1e-09 | 0 |
| GE-CHK-104-A03 | Derived gamma equals 0.90 | 1.526764539808018 | 1 | 1e-09 | 0 |

**Tolerance rationale:** The source scale factor is printed as 1.36. The retained 0.006 ratio allowance accommodates its two-decimal rounding and rounded shear inputs. This does not relax an engineering acceptance limit. Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** For gammaE = 0.90, beta = 1.526764540. With Vmodal = 100 kN, beta is one; the procedure does not reduce forces.

**Report mapping:** VtE, Vmodal and gammaE produce beta_force for its intended demand transformation. Preserve the separately reported beta_displacement = 1.00.

**Qualification:** Arithmetic is verified for the declared 0.80 branch. Irregularity classification requires its own verification, and the force scale is not copied to every displacement consumer.

**Frozen input SHA-256:** `352bebc4979cce90a9b8a5331b308ed6485a3121eee828cfe38628e046732641`

**Case SHA-256:** `204f4d659cbc8b206efc3902822851e208fcc290423b89c82d05019529850fbd`

### GE-CHK-105 — Effective drift and the infill limit

**Check:** CHK-105 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Effective relative drift with kappa = 1 in the fully adjoining brittle-infill branch.

**Normative or contract basis:** TBDY 2018 4.9.1.2 to 4.9.1.3(a), Eqs. 4.33 and 4.34a

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. PDF page 18; X +5 percent SB207 and Y +5 percent SB214 at second basement. Original PDF pages: [18]; atlas pages: [20]. X with +5 percent eccentricity at SB207 and Y with +5 percent at SB214, second basement; lambda = 0.3999, h = 4.50 m and effective drifts 44.91/67.65 mm

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| lambda | 0.3999 | 1 | Page 18 |
| effective_delta_X | 44.91 | mm | Page 18 SB207 |
| effective_delta_Y | 67.65 | mm | Page 18 SB214 |
| storey_height | 4500 | mm | Page 18, 4.50 m |
| drift_limit | 0.008 | 1 | Source-selected fully adjoining branch |

#### Calculation and intermediate results

GE-CHK-105-S01: **Multiply effective displacement by lambda and divide by height.**

Formula (display only): `r=lambda delta/h`

Substitution: `.3999×44.91/4500; .3999×67.65/4500`

Result: rX = 0.003991002 and rY = 0.006011830 (units: 1)

GE-CHK-105-S02: **Normalize by the same infill-branch limit.**

Formula (display only): `u=r/.008`

Substitution: `.003991002/.008; .006011830/.008`

Result: uX = 0.49887525 and uY = 0.75147875 (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| rX | 0.003991002 | 1 | PDF page 18, 0.00399 |
| rY | 0.00601183 | 1 | PDF page 18, 0.00601 |
| uX | 0.49887525 | 1 | Independent arithmetic recalculation |
| uY | 0.75147875 | 1 | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-105-A01 | Printed X ratio | 0.00399 | 1 | 5e-06 | 0 |
| GE-CHK-105-A02 | Printed Y ratio | 0.00601 | 1 | 5e-06 | 0 |
| GE-CHK-105-A03 | Y utilization | 0.75147875 | 1 | 1e-09 | 0 |
| GE-CHK-105-A04 | Derived 100 mm utilization | 1.1108333333333333 | 1 | 1e-09 | 0 |

**Tolerance rationale:** The source ratio is printed as 0.00399; 0.000005 is half of the final displayed decimal unit. This does not relax an engineering acceptance limit. The source ratio is printed as 0.00601; 0.000005 is half of the final displayed decimal unit. This does not relax an engineering acceptance limit. Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** For delta = 100 mm, r = 0.008886667 and utilization = 1.110833333. The flexible-joint branch requires physical connection evidence.

**Report mapping:** Reported effective delta_max and lambda produce lambda delta/h and its 0.008 comparison with member and direction identity. Begin from printed effective delta; do not force rounded joint displacements to reproduce it.

**Qualification:** The final comparison is reproduced from reported effective drift and lambda; upstream displacement differences and source scales require separate verification.

**Frozen input SHA-256:** `e18222f6303318e7a59969e7415f6f834616517ae62ec39016cbe6d31142d1fd`

**Case SHA-256:** `709d9d4525bd3a78ec7e42d46b00581caad097f83155f44c61d9d0ff55b18fa8`

### GE-CHK-106 — A1 ratio of maximum to average drift

**Check:** CHK-106 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Torsional irregularity for one storey, direction and eccentricity.

**Normative or contract basis:** TBDY 2018 Table 3.6 A1 and 3.6.2.1

#### Source trace

- **GE-S07**, 4_sikistirilmis_10MB_alti(1).pdf; SHA-256 `0c6955496aaaa92e2b508ca4eb040927ac8eab2bef92a857f2ff602b8a78fba2`. PDF page 28, printed page 26; X +5 percent, second storey. Original PDF pages: [28]; atlas pages: [36]. Maximum 4.011, minimum 3.522, average 3.766 mm and eta = 1.065

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| maximum_drift | 4.011 | mm | Page 28 selected row |
| minimum_drift | 3.522 | mm | Same source row |
| A1_threshold | 1.2 | 1 | TBDY Table 3.6 |

#### Calculation and intermediate results

GE-CHK-106-S01: **Reproduce the source diaphragm-row average.**

Formula (display only): `Delta_ort=(max+min)/2`

Substitution: `(4.011+3.522)/2`

Result: Average = 3.7665 mm, printed as 3.766 mm (units: mm)

GE-CHK-106-S02: **Calculate the torsional ratio.**

Formula (display only): `etaB=Delta_max/Delta_ort`

Substitution: `4.011/3.7665`

Result: etaB = 1.064914377, rounding to 1.065 and below 1.2 (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| average_drift_from_extremes | 3.7665 | mm | Independent arithmetic recalculation |
| etaB | 1.064914376742334 | 1 | Target 1.065 on PDF page 28 |
| A1_present | false | bool | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-106-A01 | Average drift | 3.7665 | mm | 1e-09 | 0 |
| GE-CHK-106-A02 | Printed torsional ratio | 1.065 | 1 | 0.0008 | 0 |
| GE-CHK-106-A03 | Threshold comparison | false | bool | 0 | 0 |
| GE-CHK-106-A04 | Derived A1 ratio | 1.5 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. The printed eta is 1.065 and drift inputs are rounded. The retained 0.0008 allowance permits their propagated printed-value difference. This does not relax an engineering acceptance limit. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Maximum 6 mm and minimum 2 mm give etaB = 1.5. Equality at 1.2 does not satisfy the strict greater-than threshold.

**Report mapping:** The same diaphragm row supplies extrema, the declared averaging rule, etaB and A1 classification. Other directions and eccentricities remain separate instances.

**Qualification:** The selected source-row arithmetic does not automatically generalize to multiple diaphragms or different averaging definitions. Selecting modal analysis does not erase an A1 finding.

**Frozen input SHA-256:** `ec56d027f33c7df1471ddf7d21911b84c50a5854f8d13bd5792f49cec3658c4d`

**Case SHA-256:** `c238a306c7ba1d925a5191146708dd881a8e315a55e7f51a8ce481c6f56d81bc`

### GE-CHK-107 — A2 floor-opening area ratio

**Check:** CHK-107 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Only the total-opening-area over gross-area branch of A2.

**Normative or contract basis:** TBDY 2018 Table 3.6 A2-I, A2-II and A2-III; 3.6.2.2

#### Source trace

- **GE-S08**, 17_DUZENSIZLIKLER.xlsx; SHA-256 `3fde2d386c5afb02c30ee895146926f677385bd6f5a726dd1fd5de67a4d0ffad`. Plan irregularities worksheet, J6:N6, +0.00 storey. Original PDF pages: null; atlas pages: null. Gross and opening areas at storey +0.00

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| gross_area | 3274.4050014 | m² | K6 |
| opening_area | 91.4449986 | m² | L6 |
| opening_ratio_limit | 0.3333333333333333 | 1 | A2-I threshold |

#### Calculation and intermediate results

GE-CHK-107-S01: **Calculate opening ratio.**

Formula (display only): `r=A_open/A_gross`

Substitution: `91.4449986/3274.4050014`

Result: Opening ratio = 0.027927210764, or 2.792721076 percent (units: 1)

GE-CHK-107-S02: **Compare the area branch.**

Formula (display only): `r>1/3`

Substitution: `.02792721>.33333333`

Result: A2-I is absent for this numerical instance (units: bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| opening_ratio | 0.027927210763757662 | 1 | Matches the cached value in cell N6 |
| A2_I_present | false | bool | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-107-A01 | Opening ratio | 0.027927210763757662 | 1 | 1e-09 | 0 |
| GE-CHK-107-A02 | A2-I threshold | false | bool | 0 | 0 |
| GE-CHK-107-A03 | Derived larger opening | 0.3664787952275084 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Opening area 1200 m² gives 0.366478795, above one third. A smaller opening around a column may still interrupt transfer under A2-II.

**Report mapping:** K6 and L6 with consistent area units produce N6 and A2-I. Local load-transfer discontinuity and sudden stiffness or strength changes remain separate A2-II and A2-III records.

**Qualification:** A complete area-ratio calculation does not establish the absence of every A2 subtype.

**Frozen input SHA-256:** `a55a62ded0e2a878b52ce98a753c6109a2f947f2e578b1e060d8e30d031e2c43`

**Case SHA-256:** `ac8a01d2b7224cebee46abaf212e074d5f946abe3f8d484239a4ddd8fe9a88cf`

### GE-CHK-108 — Dimensional projection limit for A3

**Check:** CHK-108 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

A dimensioned L-plan benchmark illustrating the geometry needed behind the source summary decision.

**Normative or contract basis:** TBDY 2018 Table 3.6 A3, Figure 3.3 and 3.6.2.2

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 PDF page 16: source states absence based on user inspection; no dimensions published. Original PDF pages: [16]; atlas pages: [18]. The report says no A3 irregularity, checked by the user; dimensions are not published
- **GE-S09**, 20180318M1-2-1.pdf; SHA-256 `8d3a9a463d4a534ec2c6834c557b5f706e2ad976c2d6837f6c9b6242e38a6bb2`. Standard PDF page 41, printed page 20, Table 3.6; page 43, printed page 22, Figure 3.3. Original PDF pages: [41, 43]; atlas pages: null. Definition requiring projection dimensions to exceed 20 percent in both directions

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| plan_Lx_Ly | [20, 15] | m | Selected plan dimensions for this benchmark |
| projection_ax_ay | [4.1, 3.1] | m | Selected dimensions of the same L-plan projection |

#### Calculation and intermediate results

GE-CHK-108-S01: **Calculate the projection ratio in each direction.**

Formula (display only): `rx=ax/Lx; ry=ay/Ly`

Substitution: `4.1/20; 3.1/15`

Result: rx = 0.205 and ry = 0.206666667 (units: 1)

GE-CHK-108-S02: **Apply both conditions together.**

Formula (display only): `A3=(rx>.20) and (ry>.20)`

Substitution: `(.205 > .20) and (.206667 > .20)`

Result: A3 is present; use the required in-plane floor modelling and transfer branch (units: bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| rx | 0.205 | 1 | Declared dimensioned benchmark |
| ry | 0.20666666666666667 | 1 | Independent arithmetic recalculation |
| A3_present | true | bool | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-108-A01 | X projection ratio | 0.205 | 1 | 1e-09 | 0 |
| GE-CHK-108-A02 | Y projection ratio | 0.20666666666666667 | 1 | 1e-09 | 0 |
| GE-CHK-108-A03 | Combined A3 condition | true | bool | 0 | 0 |
| GE-CHK-108-A04 | Equality at twenty percent | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-108-A03 |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-108-A04 |
| boundary | SPECIFIED_EXECUTABLE | GE-CHK-108-A04 |
| missing_source | OPEN | None |

**Narrative variant:** With ax = 4.00 m and ay = 3.10 m, rx equals 0.20 and the combined strict condition is false. An area ratio cannot replace this dimensional test.

**Report mapping:** The engine report should expose plan and projection identity, Lx, Ly, ax, ay and both ratios. These benchmark dimensions are not claimed to come from EX6.

**Qualification:** This is a complete derived geometric benchmark, not an independent numerical confirmation of the EX6 absence declaration.

**Frozen input SHA-256:** `d765e65d222e76f893f4590d2eff81f0be2a5626822433d6109baf4954f1bf78`

**Case SHA-256:** `91f2d2a2164707fc22619ec2f8aaedcfa6ebba2141b9fcae5a8e3d1f15ca369e`

### GE-CHK-109 — B1 directional effective areas and adjacent-storey ratio

**Check:** CHK-109 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

B1 ratios from the directional effective shear-area totals printed in the source.

**Normative or contract basis:** TBDY 2018 Table 3.6 B1 and 3.6.2.3

#### Source trace

- **GE-S08**, 17_DUZENSIZLIKLER.xlsx; SHA-256 `3fde2d386c5afb02c30ee895146926f677385bd6f5a726dd1fd5de67a4d0ffad`. Vertical irregularities worksheet B6:I6; +0.00 and +4.50 storeys. Original PDF pages: null; atlas pages: null. Storeys +0.00/+4.50; X areas 39/38.36 m² and Y areas 36.28/35.64 m²

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| Ae_current_X_Ae_above_X | [39, 38.36] | m² | D6 and F6 |
| Ae_current_Y_Ae_above_Y | [36.28, 35.64] | m² | E6 and G6 |
| B1_threshold | 0.8 | 1 | TBDY Table 3.6 |

#### Calculation and intermediate results

GE-CHK-109-S01: **Calculate directional area ratios.**

Formula (display only): `eta_c=Ae_i/Ae_up`

Substitution: `39/38.36; 36.28/35.64`

Result: X = 1.016684046 and Y = 1.017957351 (units: 1)

GE-CHK-109-S02: **Apply the lower threshold to the same physical adjacency.**

Formula (display only): `eta_c<.80`

Substitution: `1.016684<.80; 1.017957<.80`

Result: No B1 condition in either direction for this adjacent pair (units: bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| eta_c_X | 1.0166840458811262 | 1 | H6 |
| eta_c_Y | 1.0179573512906845 | 1 | I6 |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-109-A01 | X area ratio | 1.0166840458811262 | 1 | 1e-09 | 0 |
| GE-CHK-109-A02 | Y area ratio | 1.0179573512906845 | 1 | 1e-09 | 0 |
| GE-CHK-109-A03 | Derived contribution-total ratio | 0.75 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** An explicit derived example Aw = 20, Ag = 10, Ak = 40 m² gives Ae = 36 m². With upper Ae = 48 m², eta = 0.75 and the applicable R multiplier is 1.25 times 0.75 = 0.9375. Apply the lower-storey excess-infill exception separately.

**Report mapping:** D6/E6 and F6/G6 produce H6/I6. Production also exposes the Aw + Ag + 0.15 Ak contribution ledger with the same direction and physical scope.

**Qualification:** This recalculates source Ae-total ratios, not independent component geometry. The 36/48 example is a declared derived scenario.

**Frozen input SHA-256:** `4a0eeaa44570efe02aeba23151a589a19719a08ad52b6d098d907d799c060003`

**Case SHA-256:** `26f8d40d32c28e49f03df22bcdef25927ecac519bed2a013d314d4507f7f07cc`

### GE-CHK-110 — B2 comparison with both adjacent storeys

**Check:** CHK-110 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Stiffness-irregularity ratios for the same direction and eccentricity outside basement exclusions.

**Normative or contract basis:** TBDY 2018 Table 3.6 B2 and 3.6.2.1

#### Source trace

- **GE-S07**, 4_sikistirilmis_10MB_alti(1).pdf; SHA-256 `0c6955496aaaa92e2b508ca4eb040927ac8eab2bef92a857f2ff602b8a78fba2`. PDF page 30, printed page 28, first-storey X +5 percent row. Original PDF pages: [30]; atlas pages: [37]. First-storey drift 5.865, upper second-storey drift 3.766 and lower ground-storey drift 4.816 mm; every height is 5 m

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| drift_current_above_below | [5.865, 3.766, 4.816] | mm | Page 30, same directional and eccentricity family |
| height_current_above_below | [5000, 5000, 5000] | mm | Same table |
| B2_threshold | 2 | 1 | TBDY Table 3.6 |

#### Calculation and intermediate results

GE-CHK-110-S01: **Calculate average drift over height.**

Formula (display only): `ri=Delta_i/hi`

Substitution: `5.865/5000; 3.766/5000; 4.816/5000`

Result: 0.001173, 0.0007532 and 0.0009632 (units: 1)

GE-CHK-110-S02: **Calculate both adjacent-storey ratios.**

Formula (display only): `eta_up=ri/rup; eta_down=ri/rdown`

Substitution: `5.865/3.766; 5.865/4.816`

Result: Upper ratio = 1.557355284, printed 1.56; lower ratio = 1.217815615, printed 1.22 (units: 1)

GE-CHK-110-S03: **Classify the larger ratio.**

Formula (display only): `max(eta_up, eta_down)>2`

Substitution: `1.557355284>2`

Result: No B2 condition for this first-storey instance (units: bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| eta_up | 1.5573552841210834 | 1 | Printed 1.56 on PDF page 30 |
| eta_down | 1.2178156146179402 | 1 | Printed 1.22 on PDF page 30 |
| B2_present | false | bool | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-110-A01 | Upper-neighbour ratio | 1.56 | 1 | 0.008 | 0 |
| GE-CHK-110-A02 | Lower-neighbour ratio | 1.22 | 1 | 0.008 | 0 |
| GE-CHK-110-A03 | Combined classification | false | bool | 0 | 0 |
| GE-CHK-110-A04 | Derived B2 exceedance | 2.1242697822623473 | 1 | 1e-09 | 0 |

**Tolerance rationale:** The neighbouring-storey ratio is printed as 1.56 from rounded drift inputs. The retained 0.008 allowance is a printed-value comparator. This does not relax an engineering acceptance limit. The neighbouring-storey ratio is printed as 1.22 from rounded drift inputs. The retained 0.008 allowance is a printed-value comparator. This does not relax an engineering acceptance limit. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance. Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Changing first-storey drift to 8 mm gives upper ratio 2.124269782, above two. Retain the finding and its method-selection consequences.

**Report mapping:** Use dimensional Delta and h from all three same-family rows, then compare both neighbours. Avoid redividing prematurely rounded ratios such as 0.00117.

**Qualification:** Both adjacent comparisons match printed rounding. Other directions and eccentricities require their own instances.

**Frozen input SHA-256:** `69f2951763a158e2c2196f0dc6c7edce90a15d69ed528e826dbeda60da8b3131`

**Case SHA-256:** `1eb14038a8733ff91c4b7c0a570e4330114a18857f72f67734a93f62448e4ff2`

### GE-CHK-111 — B3 support-topology benchmark

**Check:** CHK-111 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

An upper column whose bottom end bears on the free end of a cantilever beam.

**Normative or contract basis:** TBDY 2018 3.6.2.4(a) and (b)

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 PDF page 16: reported B3 absence without a published connectivity graph. Original PDF pages: [16]; atlas pages: [18]. The report says no B3 irregularity; no numerical connectivity graph is published
- **GE-S09**, 20180318M1-2-1.pdf; SHA-256 `8d3a9a463d4a534ec2c6834c557b5f706e2ad976c2d6837f6c9b6242e38a6bb2`. Standard PDF page 44, printed page 23: cantilever and two-ended support branches. Original PDF pages: [44]; atlas pages: null. Branches for a column resting on a cantilever end or a beam supported at both ends

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| beam_end_A | [0, 0, 0] | m | Selected supported end |
| beam_end_B | [5, 0, 0] | m | Selected free end |
| upper_column_I_J | [5, 0, 0, 5, 0, 3] | m | Selected column I and J coordinates |
| lower_vertical_at_B | false | bool | Declared benchmark topology |

#### Calculation and intermediate results

GE-CHK-111-S01: **Match the column bottom and beam end.**

Formula (display only): `distance(column_I, beam_B)`

Substitution: `sqrt((5−5)²+(0−0)²+(0−0)²)`

Result: Connection distance is zero; the members share a physical node (units: m)

GE-CHK-111-S02: **Classify the support topology.**

Formula (display only): `supported_ends=1; column_on_free_end=True`

Substitution: `A is supported, B is free; column at B`

Result: A is supported and B is free; the upper column at B falls under the prohibited branch in 3.6.2.4(a) (units: count; bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| connection_distance | 0 | m | Independent arithmetic recalculation |
| B3_present | true | bool | Independent arithmetic recalculation |
| cantilever_column_permitted | false | bool | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-111-A01 | End-coordinate match | 0 | m | 1e-09 | 0 |
| GE-CHK-111-A02 | Supported-end count | 1 | count | 1e-09 | 0 |
| GE-CHK-111-A03 | Beam span | 5 | m | 1e-09 | 0 |
| GE-CHK-111-A04 | Derived two-supported-end count | 2 | count | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Extending the beam to C = (10,0,0) m with supports at A and C places the column at B = (5,0,0) m within a supported span. Under 3.6.2.4(b), vertical earthquake analysis under 4.4.3 is required. This is not the cantilever prohibition or an absence of B3 geometry.

**Report mapping:** The detailed report must expose column and beam Unique IDs, common joint, both end supports and applicable 3.6.2.4 branch. This graph is a new code benchmark.

**Qualification:** The derived topology does not verify the actual EX6 connectivity inventory or its reported absence.

**Frozen input SHA-256:** `f724e282df9408a3dd6d1b53d278307f370bf612252fd1b59c8842468c23630a`

**Case SHA-256:** `870a817086e47ba8d9e6094a1d7c92da1a8e27fef8255e58a36dc7e5933330e3`

### GE-CHK-112 — Wall overturning-moment share

**Check:** CHK-112 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Arithmetic of one X-direction source row with a separately selected high-ductility frame-and-wall system profile.

**Normative or contract basis:** TBDY 2018 4.3.4.5 to 4.3.4.8 and Eq. 4.2 for the selected system

#### Source trace

- **GE-S10**, 14_PERDE_DEVRILME_MOMENT_KONTROLU.xlsx; SHA-256 `aeecc15fa9c22694db31b35f61ac28fac60aa1cccaf17fc77aec6b04342354dd`. Devrilme_Moment_Kontrolu_423!C7:C11, X direction. Original PDF pages: null; atlas pages: null. X direction M0 = 18998.915 and Mdev = 2199.1413 tonf*m; ratio in C9

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| total_overturning_moment | 18998.915 | tonf·m | C7 |
| wall_overturning_moment | 2199.1413 | tonf·m | C8 |
| system_profile | high-ductility frame plus wall system | role | Selected 4.3.4.5 branch |

#### Calculation and intermediate results

GE-CHK-112-S01: **Calculate the moment ratio with the same direction and reference.**

Formula (display only): `r=sum(Mdev)/M0`

Substitution: `2199.1413/18998.915`

Result: Share = 0.115750888932, or 11.575088893 percent (units: 1)

GE-CHK-112-S02: **Evaluate the selected branch limits.**

Formula (display only): `.40<r<.75`

Substitution: `.40<.115750889<.75`

Result: The lower condition is not met; record the R, D and BYS decision branch in 4.3.4.5 (units: bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| wall_overturning_share | 0.11575088893234164 | 1 | Matches the cached value in cell C9 |
| lower_share_condition | false | bool | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-112-A01 | Wall overturning share | 0.11575088893234164 | 1 | 1e-09 | 0 |
| GE-CHK-112-A02 | Lower-share condition | false | bool | 0 | 0 |
| GE-CHK-112-A03 | Derived fifty-percent share | 0.5 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** At wall moment 0.40 times M0 = 7599.566 tf·m, the strict lower inequality is still not satisfied. A 0.50 M0 value gives share 0.50. A system-profile change also changes the governing rule.

**Report mapping:** C7 and C8 give X-direction share and the selected system decision. The Y-direction references are not used in this example.

**Qualification:** The X-cell ratio is reproduced. Same-cut and same-direction lineage of the wall total requires its source artifact; this ratio alone is not whole-building acceptance.

**Frozen input SHA-256:** `b22c3bb42214c88b0e50728977782b75fe6066578e54a9cc50e7c9ab829bebbd`

**Case SHA-256:** `f57d79a8cef39a1da9bd2b5136b1ea0eacb8469d82480714d3c570a3d6faccc7`

### GE-CHK-113 — Numerical trace of the second-order indicator

**Check:** CHK-113 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

thetaII from average reduced storey drift and the betaII branch for this concrete profile.

**Normative or contract basis:** TBDY 2018 4.9.2.1 to 4.9.2.2, Eqs. 4.35 and 4.36

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. PDF pages 1 and 19; X +5 percent, second basement, R = 8 and D = 3. Original PDF pages: [1, 19]; atlas pages: [13, 21]. X with +5 percent eccentricity at the second basement: average drift 4.85 mm, total weight 2050.03 tf, shear 187.26 tf, h = 4.5 m, R = 8 and D = 3

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| average_reduced_drift | 4.85 | mm | Page 19 selected row |
| weight_above | 2050.03 | tf | Same source row |
| storey_shear | 187.26 | tf | Same source row |
| storey_height | 4.5 | m | Same source row |
| R_D_Ch | [8, 3, 0.5] | 1 | R and D from page 1; Ch from the concrete branch |

#### Calculation and intermediate results

GE-CHK-113-S01: **Make length units consistent.**

Formula (display only): `Delta=4.85/1000`

Substitution: `4.85mm→.00485 m`

Result: 4.85 mm = 0.00485 m (units: m)

GE-CHK-113-S02: **Calculate the stability indicator.**

Formula (display only): `theta=Delta_avg sumw/(Vh)`

Substitution: `.00485×2050.03/(187.26×4.5)`

Result: thetaII = 0.011798978841, printed as 0.0118 (units: 1)

GE-CHK-113-S03: **Calculate the threshold and amplification branch.**

Formula (display only): `theta_lim=.12D/(ChR); beta=1 if theta≤theta_lim`

Substitution: `.12×3/(.5×8)=.09; .01179898≤.09`

Result: theta_limit = 0.09 and betaII = 1.000 (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| thetaII | 0.011798978841064713 | 1 | Printed 0.0118 on PDF page 19 |
| theta_limit | 0.09 | 1 | Independent arithmetic recalculation |
| betaII | 1 | 1 | Printed 1.000 on PDF page 19 |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-113-A01 | Printed theta target | 0.0118 | 1 | 5e-05 | 0 |
| GE-CHK-113-A02 | Theta threshold | 0.09 | 1 | 1e-09 | 0 |
| GE-CHK-113-A03 | Threshold comparison | true | bool | 0 | 0 |
| GE-CHK-113-A04 | Derived threshold exceedance | 0.0973111656995028 | 1 | 1e-09 | 0 |
| GE-CHK-113-A05 | Derived betaII amplification | 1.0097482209326705 | 1 | 1e-09 | 0 |

**Tolerance rationale:** The source theta is printed as 0.0118. A 0.00005 ratio allowance is half the final displayed decimal unit. This does not relax an engineering acceptance limit. Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-113-A03 |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** For average drift 40 mm, theta = 0.097311166 exceeds 0.09 and betaII = 0.88 + (0.5 times 8/3) theta = 1.009748221. Do not feed an R/I-amplified effective drift back into theta.

**Report mapping:** The same X +5 percent row supplies drift, shear and weight. Normalize mm to m before theta, then apply R, D and Ch. Native geometric PDelta and local TS 500 beta remain separate effect records.

**Qualification:** The published drift, shear and weight reproduce the indicator. They do not replace evidence of native PDelta initial state or convergence.

**Frozen input SHA-256:** `91ff08e9064c9eb0e99a4a918578a143e7e7c9e450b794e52756f137c9c99367`

**Case SHA-256:** `65ec6661b2f59bfa937a51be211c2cb961b706b521377bcf884a1f9d7a505be1`

### GE-CHK-114 — Base transfer vector from storey forces

**Check:** CHK-114 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Resultants of the reported X +5 percent external loads and the action-reaction convention for foundation transfer.

**Normative or contract basis:** Equilibrium and common-reference transformation; TBDY 2018 4.7.2.6 Eq. 4.25

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. PDF pages 12 to 14; X +5 percent storey forces, elevations and torsional loads. Original PDF pages: [12, 13, 14]; atlas pages: [15, 16, 17]. X with +5 percent eccentricity: storey forces 187.2624 and 55.4117 tf; elevations 7.30 and 2.80 m; torsions 253.7406 and 75.0828 tfm

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| storey_Fx | [187.2624, 55.4117] | tf | Page 12 X +5 percent |
| storey_z | [7.3, 2.8] | m | Page 14 same storeys |
| storey_Mz | [253.7406, 75.0828] | tf·m | Page 12 same torsional-load family |
| reference_origin | [0, 0, 0] | m | Explicit benchmark base-reference choice |

#### Calculation and intermediate results

GE-CHK-114-S01: **Sum horizontal forces from the same loading state.**

Formula (display only): `Fx_base=sum(Fxi)`

Substitution: `187.2624+55.4117`

Result: Fx = 242.6741 tf (units: tf)

GE-CHK-114-S02: **Calculate overturning and torsional resultants at the base.**

Formula (display only): `My=sum(zFx); Mz=sum(Mzi)`

Substitution: `7.3×187.2624+2.8×55.4117; 253.7406+75.0828`

Result: My = 1522.16828 tf·m, printed 1522.17; Mz = 328.8234 tf·m (units: tf*m)

GE-CHK-114-S03: **Distinguish support reaction from applied foundation load.**

Formula (display only): `R_support=−F_external; F_to_foundation=−R_support`

Substitution: `Rx_support=−242.6741; Mysupport=−1522.16828`

Result: Support reactions oppose the external resultant; the superstructure load on the foundation has the external-resultant sign (units: tf; tf*m)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Fx_external | 242.6741 | tf | Independent arithmetic recalculation |
| My_external | 1522.16828 | tf·m | Printed 1522.17 on PDF page 13 |
| Mz_external | 328.8234 | tf·m | Independent arithmetic recalculation |
| Rx_support | -242.6741 | tf | Independent arithmetic recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-114-A01 | Base horizontal force | 242.6741 | tf | 1e-09 | 0 |
| GE-CHK-114-A02 | Printed overturning moment | 1522.17 | tf·m | 0.005 | 0 |
| GE-CHK-114-A03 | Torsional resultant | 328.8234 | tf·m | 1e-09 | 0 |
| GE-CHK-114-A04 | Reference-elevation transport | 1279.49418 | tf·m | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. The base moment is printed as 1522.17 tf*m. The 0.005 tf*m allowance is half the final displayed decimal unit. This does not relax an engineering acceptance limit.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Moving the reference to z = 1 m changes My to 1522.16828 - 242.6741 = 1279.49418 tf·m. Renaming the reference without transporting the moment is incorrect.

**Report mapping:** Storey loads and elevations produce a common-reference resultant, followed by explicit superstructure reaction and foundation-load signs. Native frame, pier and joint contributions require separate reconciliation.

**Qualification:** This derives external-load resultants and reference transport. Native base reactions are not fully provided, and unpublished Fz is not assigned a zero value.

**Frozen input SHA-256:** `1cd840993d98c523b29be01a2c86c4f3d2e42a31b04065c9e5ac7ea044d8e966`

**Case SHA-256:** `ad3726700089728c0a511847505b1a866933e762ef85462c0d8b45154db428bb`

### GE-CHK-115 — S1 minimum eccentricity about both axes

**Check:** CHK-115 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Minimum moment of a square section in compression; source 11/22 labels require an explicit map before becoming CSI M2/M3.

**Normative or contract basis:** TS 500 2000 6.3.10 Eq. 6.16; minimum demand before moment magnification

#### Source trace

- **GE-S05**, col1.docx; SHA-256 `75e14b85d28958e13b59e77cf12242ef6bf2546492754cd33ac9b900e45fc0de`. COL1 S1 (D-4), Storey 1, Critical Loading 16 (Gc+Ez+Ey+). Original PDF pages: null; atlas pages: null. 30 by 30 cm section, Nd = 7.430 t, M11 = 2.39 and M22 = 1.03 t*m; reported minimum moments 0.18/0.18 t*m

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| section_depth | 300 | mm | COL1 S1 |
| Nd | 7.43 | t | Same source force unit and combination 16 |
| M11 | 2.39 | t·m | Same source row |
| M22 | 1.03 | t·m | Same source row |

#### Calculation and intermediate results

GE-CHK-115-S01: **Calculate minimum eccentricity in each direction.**

Formula (display only): `emin=15+0.03h`

Substitution: `15+0.03×300`

Result: emin = 24 mm = 0.024 m (units: mm)

GE-CHK-115-S02: **Calculate compression-induced minimum moment.**

Formula (display only): `Mmin=Nd emin`

Substitution: `7.430×0.024`

Result: Mmin = 0.17832 source t·m, rounding to 0.18 (units: source t*m)

GE-CHK-115-S03: **Select design moment magnitudes.**

Formula (display only): `|Mdesign,i|=max(|Mi|,Mmin)`

Substitution: `max(2.39,0.17832); max(1.03,0.17832)`

Result: Design magnitudes remain 2.39 and 1.03 source t·m (units: source t*m)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| emin_11_mm | 24 | mm | Independent arithmetic |
| emin_22_mm | 24 | mm | Independent arithmetic |
| minimum_moment | 0.17832 | t·m | Independent arithmetic |
| design_magnitudes | [2.39, 1.03] | t·m | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-115-A01 | Minimum eccentricity | 24 | mm | 1e-09 | 0 |
| GE-CHK-115-A02 | Minimum moment | 0.17832 | source t·m | 1e-09 | 0 |
| GE-CHK-115-A03 | Both design moment magnitudes | [2.39, 1.03] | source t·m | 1e-09 | 0 |
| GE-CHK-115-A04 | Low-moment variant | 0.17832 | source t·m | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Setting M22 to 0.10 gives 0.17832 in that direction. A 300 by 500 mm variant gives 24 and 30 mm eccentricities; an axis swap must be detected. Zero moment requires an explicit sign policy.

**Report mapping:** Source Nd and dimensions give emin and Nd emin, then MinimumEccentricityDemand. The printed 0.18 entry is an intermediate comparison.

**Qualification:** This verifies minimum-moment arithmetic, not COL1 biaxial capacity or a live CSI axis transformation.

**Frozen input SHA-256:** `baf704d61da763500380eaa5d01b201f431c3bc1ea631895dba80730e0f0abcc`

**Case SHA-256:** `ced15f39802369279ae5a3b223beb5f14c82ff74b11bbc973379cc4e37641126`

### GE-CHK-116 — Sway1 slenderness using clear length and exact inertia

**Check:** CHK-116 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Exact I/A geometry using reported clear length and rounded k; physical face coordinates are not independently supplied.

**Normative or contract basis:** TS 500 2000 7.6.2.3; exact radius sqrt(I/A) and permitted rectangular approximation 0.3h are separate methods

#### Source trace

- **GE-S11**, sway1.docx; SHA-256 `6e8863ae52834af5febbdd30db0648de186a713f7da991e05db660bb2425b0d7`. SWAY1 moment magnification, S1 Storey 3, X/Y; L = 255 cm, k = 0.90, reported slenderness 26. Original PDF pages: null; atlas pages: null. 30 by 30 cm section, Lx = Ly = 255 cm, k = 0.90 and approximate reported Lk/i = 26

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| section_depth | 300 | mm | SWAY1 S1 |
| clear_length | 2550 | mm | Source L = 255 cm |
| effective_length_factor | 0.9 | 1 | Source k rounded to two decimals |

#### Calculation and intermediate results

GE-CHK-116-S01: **Calculate section geometry.**

Formula (display only): `A=bh; I=bh³/12; i=sqrt(I/A)`

Substitution: `A=300×300; I=300×300³/12`

Result: A = 90000 mm², I = 675000000 mm⁴ and radius = 86.60254038 mm (units: mm²; mm⁴; mm)

GE-CHK-116-S02: **Calculate effective length and slenderness.**

Formula (display only): `lk=k ln; λ=lk/i`

Substitution: `0.90×2550; 2295/86.60254038`

Result: lk = 2295 mm and exact slenderness = 26.50037736 (units: mm; 1)

GE-CHK-116-S03: **Reproduce the approximate-radius branch.**

Formula (display only): `i≈0.3h; λapprox=lk/(0.3h)`

Substitution: `2295/90`

Result: Approximate-radius slenderness = 25.5, displayed as 26 at whole-number precision (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| A | 90000 | mm² | Independent arithmetic |
| I | 675000000 | mm⁴ | Independent arithmetic |
| lk | 2295 | mm | Independent arithmetic |
| lambda_exact | 26.500377355803824 | 1 | Independent arithmetic |
| lambda_approx | 25.5 | 1 | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-116-A01 | Section inertia | 675000000 | mm⁴ | 1e-09 | 0 |
| GE-CHK-116-A02 | Effective length | 2295 | mm | 1e-09 | 0 |
| GE-CHK-116-A03 | Exact slenderness | 26.500377355803824 | 1 | 1e-09 | 0 |
| GE-CHK-116-A04 | Approximate-radius branch | 25.5 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** A 3000 mm joint length with faces 225 mm inward at each end gives 2550 mm clear length. Using a final force station of 2.70 m as clear length instead gives slenderness 28.05922 and contradicts the face geometry.

**Report mapping:** Reported Lx/Ly, selected k and the chosen I/A method produce FreeLengthAndSlendernessFeature. Exact and approximate radius results retain different method identifiers.

**Qualification:** This checks the selected exact-radius branch. The source approximation i = 0.3h is not labelled erroneous.

**Frozen input SHA-256:** `fd6aed5d618ce58adce8d2b3a14e7c648ba4da3dd2556e7eeb41383df165a96f`

**Case SHA-256:** `95a7bf2fda2c2be41f6fdbcdda8d5b88e8c56217e3b5c0e40f492a163b6243f3`

### GE-CHK-117 — Sway1 effective-length factor from end stiffness ratios

**Check:** CHK-117 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

The restrained-sway branch with supplied end stiffness ratios; the EI/L contribution inventory is a separate prerequisite.

**Normative or contract basis:** TS 500 2000 7.6.2.2, effective-length approximation for a sway-restrained column

#### Source trace

- **GE-S11**, sway1.docx; SHA-256 `6e8863ae52834af5febbdd30db0648de186a713f7da991e05db660bb2425b0d7`. SWAY1 S1 Storey 3; GBot = GTop = 1.975, L = 255 cm, reported k = 0.90. Original PDF pages: null; atlas pages: null. GBot = GTop = 1.975, L = 255 cm and reported k = 0.90

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| alpha1 | 1.975 | 1 | SWAY1 GBot |
| alpha2 | 1.975 | 1 | SWAY1 GTop |
| clear_length | 2550 | mm | SWAY1 clear length |

#### Calculation and intermediate results

GE-CHK-117-S01: **Calculate the three k bounds.**

Formula (display only): `k=min(0.70+0.05(α1+α2),0.85+0.05αmin,1)`

Substitution: `min(0.8975,0.94875,1)`

Result: k = min(0.8975, 0.94875, 1) = 0.8975, displayed as 0.90 (units: 1)

GE-CHK-117-S02: **Retain unrounded effective length.**

Formula (display only): `lk=k ln`

Substitution: `0.8975×2550`

Result: lk = 2288.625 mm (units: mm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| k | 0.8975 | 1 | Independent arithmetic |
| source_rounded_k | 0.9 | 1 | Report printed to two decimal places |
| lk_unrounded | 2288.625 | mm | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-117-A01 | Minimum k branch | 0.8975 | 1 | 1e-09 | 0 |
| GE-CHK-117-A02 | Effective length | 2288.625 | mm | 1e-09 | 0 |
| GE-CHK-117-A03 | Report rounding | 0.9 | 1 | 1e-09 | 0 |
| GE-CHK-117-A04 | Ideal fixed-end limit | 0.7 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Zero end ratios give k = 0.70 in the ideal benchmark. Missing neighbouring-beam EI/L cannot be substituted with zero; the formula is then not qualified.

**Report mapping:** The supplied end ratios, method and sway classification produce candidate k values, selected k and unrounded lk in EffectiveLengthFeature.

**Qualification:** The supplied end ratios are not independently recomputed. This case retains k = 0.8975 while CHK-116 intentionally uses the source-rounded 0.90.

**Frozen input SHA-256:** `083d0ec66278d4cd0c56439c61127f559529f0fbc392ba9ac2f8c038b5993ccd`

**Case SHA-256:** `41f6d0835d0907a57f2ff60708491f12a0372b00b2d7eca56bce664a138d2aa1`

### GE-CHK-118 — Single ownership of PDelta effects and analysis generation

**Check:** CHK-118 · **Kind:** CONTRACT_FIXTURE · **Population:** PRIMARY_CHECK_EXAMPLE

Consistency of three analysis identities and two effect identities; no live getter/setter is exercised.

**Normative or contract basis:** TS 500 2000 7.6, TBDY 2018 4.9.2 and SecondOrderOwnershipDecision; physical effects represented in analysis do not automatically discharge code obligations

#### Source trace

- **GE-S11**, sway1.docx; SHA-256 `6e8863ae52834af5febbdd30db0648de186a713f7da991e05db660bb2425b0d7`. SWAY1 story beta_s and member beta report columns; 100 kN·m and generation identifiers below are selected fixture data. Original PDF pages: null; atlas pages: null. Report structure separating global and local magnification; 100 kNm and identities below are new contract-fixture values

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| case_initial_state | ["RSX", "PDELTA_G", "GEN-2"] | identifier | Explicit fixture |
| case_and_force_generation | ["GEN-2", "GEN-2"] | identifier | Explicit fixture |
| moment_after_global_analysis | 100 | kN·m | Selected demand assumed to contain the proven global effect |
| local_factor | 1.2 | 1 | Selected factor for the distinct local effect |
| effect_keys | ["GLOBAL_FRAME_PDELTA", "LOCAL_MEMBER_PDELTA"] | identifier | Separate physical-effect scopes |

#### Calculation and intermediate results

GE-CHK-118-S01: **Bind demand lineage.**

Formula (display only): `generation(case)=generation(force)=generation(initial_state)`

Substitution: `GEN-2=GEN-2=GEN-2`

Result: Case, force and initial-state generations all equal GEN-2 (units: generation)

GE-CHK-118-S02: **Apply the remaining local effect once.**

Formula (display only): `Mfinal=M_after_global × βlocal`

Substitution: `100×1.20`

Result: Final moment = 120 kN·m (units: kNm)

GE-CHK-118-S03: **Expose duplicate application.**

Formula (display only): `Mduplicate=M_after_global × 1.20 × 1.20`

Substitution: `100×1.20×1.20`

Result: Duplicate application gives 144 kN·m and is rejected for this fixture (units: kNm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| M_final | 120 | kN·m | Declared contract result |
| duplicate_application | 144 | kN·m | Derived result that must be rejected |
| generation_match | true | boolean | Contract |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-118-A01 | One local application | 120 | kN·m | 1e-09 | 0 |
| GE-CHK-118-A02 | Detectable duplicate application | 144 | kN·m | 1e-09 | 0 |
| GE-CHK-118-A03 | Matching generations | true | bool | 0 | 0 |
| GE-CHK-118-A04 | Stale generation | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-118-A03 |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-118-A04 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | SPECIFIED_EXECUTABLE | GE-CHK-118-A04 |

**Narrative variant:** GEN-1 forces with GEN-2 case settings fail even if the arithmetic gives 120. Two owners applying GLOBAL_FRAME_PDELTA also fail. The local obligation is not automatically removed.

**Report mapping:** Case stiffness source, initial state, convergence and generation feed an effect matrix. Record the immutable base demand and each applied effect_id and owner.

**Qualification:** A real acceptance requires stiffness source, initial case, nonlinearity, convergence and generation from the same ETABS session. Method equivalence needs its own justification.

**Frozen input SHA-256:** `f323e90ea109011e0e0536c2aa6374c86b1ed783c2ec1dbdca49fe3486774ed6`

**Case SHA-256:** `0c147c2e4f14e9013efd6651ae1632fb2bb6ca11d66737a2d7853f891e0ae1fc`

### GE-CHK-119 — Golden 02 member beta and storey beta_s

**Check:** CHK-119 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Reproduce source magnification arithmetic while retaining a separate decision on the 1.85 adopted factor.

**Normative or contract basis:** TS 500 2000 Eqs. 7.19, 7.24 and 7.27 to 7.29; multiplication applies only when the Eq. 7.29 conditions are established

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. 2.pdf page 186, printed page 184, ground-storey SZ01 major-axis row Nd = 471.11 kN. Original PDF pages: [186]; atlas pages: [11]. Nd, Nk, Cm, storey totals and printed beta = 1.55, beta_s = 1.19 and adopted beta = 1.85

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| Nd | 471.11 | kN | GOLDEN-02 SZ01 major axis |
| Nk | 1727.29 | kN | Same row |
| Cm | 1 | 1 | Same row |
| effective_length | 5.23 | m | Same row |
| storey_sum_Nd | 1975.94 | kN | Same-storey total |
| storey_sum_Nk | 15894.39 | kN | Same-storey total |
| larger_end_moment_magnitude | 53.13 | kN·m | Magnitude of source -53.13; TS 500 end-moment notation |

#### Calculation and intermediate results

GE-CHK-119-S01: **Calculate the member factor.**

Formula (display only): `β=max(1,Cm/(1−1.3Nd/Nk))`

Substitution: `1/(1−1.3×471.11/1727.29)`

Result: beta = 1.549351615, printed 1.55 (units: 1)

GE-CHK-119-S02: **Calculate the storey factor.**

Formula (display only): `βs=max(1,1/(1−1.3ΣNd/ΣNk))`

Substitution: `1/(1−1.3×1975.94/15894.39)`

Result: beta_s = 1.192764971, printed 1.19 (units: 1)

GE-CHK-119-S03: **Explain the printed adopted-factor arithmetic.**

Formula (display only): `β×βs`

Substitution: `1.549351615×1.192764971`

Result: Product = 1.848012334, printed 1.85 (units: 1)

GE-CHK-119-S04: **Keep the method-branch decision separate.**

Formula (display only): `General sway branch: max(beta, beta_s); use beta*beta_s only if Eq. 7.29 applicability is established`

Substitution: `Maximum = 1.549351615; product = 1.848012334`

Result: The maximum is 1.549351615 and the product 1.848012334; adopt only the branch supported by evidence; the printed 1.85 is not an authorized design factor without the applicability evidence (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| beta_member | 1.5493516150646682 | 1 | Independent arithmetic |
| beta_story | 1.1927649705815875 | 1 | Independent arithmetic |
| beta_product | 1.848012333563144 | 1 | Independent arithmetic |
| source_adopted_beta | 1.85 | 1 | Printed source |
| story_stability_ratio | 0.1243168187014412 | 1 | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-119-A01 | Member beta | 1.5493516150646682 | 1 | 1e-09 | 0 |
| GE-CHK-119-A02 | Storey beta_s | 1.1927649705815875 | 1 | 1e-09 | 0 |
| GE-CHK-119-A03 | Factor product | 1.848012333563144 | 1 | 1e-09 | 0 |
| GE-CHK-119-A04 | Printed adopted factor | 1.85 | 1 | 1e-09 | 0 |
| GE-CHK-119-A05 | Storey stability inequality | true | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Nd = Nk/1.3 produces a zero denominator and no finite beta. Where Eq. 7.29 does not apply, the derived adopted factor is 1.549351615 rather than the product.

**Report mapping:** The same member and storey totals produce separate beta and beta_s fields, then Eq. 7.29 branch evidence and the adopted LocalSecondOrderDemand. Retain printed 1.85 as source_reported.

**Qualification:** The source 1.85 is explained arithmetically. EI, creep ratio, selected-cage steel inertia, effective length and Eq. 7.29 qualification are not independently established by that page.

**Frozen input SHA-256:** `a61da4c8b27fb9ff5975ce5444df4285f6e8c0e3baba17fe2a59a67cfd04f19b`

**Case SHA-256:** `29dddfeb669653173417b6565d347b6ed35c88d408d55509a90cbcbf8fd87517`

### GE-CHK-120 — Independent section resultants with partial bar-hole subtraction

**Check:** CHK-120 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Asymmetric three-bar 400 by 600 mm section, followed by a separate symmetric four-bar N = 0 uniaxial capacity point.

**Normative or contract basis:** TS 500 2000 6.2.5, 7.1 and Table 7.1; declared material, strain and sign model

#### Source trace

- **GE-S12**, exact_bar_hole_hand_resultants.json; SHA-256 `464b3ace47b4f9b532ae0782f1f86ab51a05919df7b400510b6b0f3df93a4707`. Independent oracle direct_case, derivation, symmetry_case, fixed_n_case and proportional_case. Original PDF pages: null; atlas pages: null. N/M2/M3, strain and constant-N resistance retained from an independent hand calculation; the fixture explicitly is not production-engine output

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| section_b_h | [400, 600] | mm | Oracle section |
| fck_fyk_gamma_c_gamma_s | [35, 420, 1.5, 1.15] | MPa / 1 | Oracle material |
| ultimate_strain_k1 | [0.003, 0.79] | 1 | Declared oracle model |
| bar_x2_x3_diameter | [[-150, -200, 20], [150, 150, 20], [0, 60, 20]] | mm | Direct-case coordinates |
| theta_c | [0, 253.1645569620253] | rad / mm | Direct-case strain plane |
| steel_stresses | [-229.5, 365.2173913043478, 126] | MPa | Strain compatibility with stress bounded by plus or minus fyd |

#### Calculation and intermediate results

GE-CHK-120-S01: **Calculate compression block and bar-hole moments.**

Formula (display only): `a=k1c=200; Ah=1.5πr²; Qh2=150πr²+2r³/3; Qh3=180πr²`

Substitution: `r=10; Ag=120000; Qg2=12000000`

Result: a = 200 mm; Ah = 471.238898 mm²; Qh2 = 47790.556471 mm³; Qh3 = 56548.667765 mm³ (units: mm; mm²; mm³)

GE-CHK-120-S02: **Calculate axial equilibrium.**

Formula (display only): `N=0.85fcd(Ag−Ah)+ΣσsAs`

Substitution: `(0.85×35/1.5)(120000−1.5π100)+π100(−229.5+420/1.15+126)`

Result: N = 2452874.705239 N (units: N)

GE-CHK-120-S03: **Calculate signed biaxial resultants.**

Formula (display only): `M2=ΣF x3; M3=−ΣF x2`

Substitution: `Concrete contribution plus signed moment contributions from three bars`

Result: M2 = 32883869.851034 N·mm and M3 = -265077550.775592 N·mm (units: N*mm)

GE-CHK-120-S04: **Use the separate symmetric four-bar control point.**

Formula (display only): `9401c²+147518.2637337816c−18849555.92153876=0`

Substitution: `c=37.6141719521 mm; N=0; bars=(±150,±250), Φ20`

Result: c = 37.6141719521 mm; N = 0; M3 capacity = -81268590.394755 N·mm; half demand has utilization 0.5 (units: mm; N; N*mm; 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| N | 2452874.705239413 | N | Independent reference calculation |
| M2 | 32883869.851033997 | N·mm | Independent reference calculation |
| M3 | -265077550.7755922 | N·mm | Independent reference calculation |
| minimum_bar_strain | -0.0011475 | 1 | Independent reference calculation |
| symmetric_fixed_N_capacity | 81268590.39475535 | N·mm | Separate four-bar independent calculation |
| half_demand_utilization | 0.5 | 1 | Separate four-bar independent calculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-120-A01 | Axial resultant | 2452874.705239413 | N | 1e-06 | 0 |
| GE-CHK-120-A02 | Local 2 resultant | 32883869.851033997 | N·mm | 0.0001 | 0 |
| GE-CHK-120-A03 | Local 3 resultant | -265077550.7755922 | N·mm | 0.0001 | 0 |
| GE-CHK-120-A04 | Positive fixed-N root | 37.61417195211549 | mm | 1e-09 | 0 |
| GE-CHK-120-A05 | Half-capacity demand | 0.5 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-06 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Inherited absolute allowance 0.0001 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** The C bar lies on the block boundary: subtracting a full disk or no disk instead of a half disk changes N and M3. Reflection of bars with theta plus pi preserves N and reverses both moments. Missing a required case or cut still prevents coverage acceptance.

**Report mapping:** Material and bar coordinates define strain plane, concrete area minus bar holes, first moments and steel/concrete resultants, then the numerical FinalPMMResult check. Do not combine this capacity with COL1 S1.

**Qualification:** The three-bar arrangement is a numerical-resultant benchmark, not a code-compliant column cage. The separate four-bar case checks one fixed-N point; it does not establish an entire PMM surface, spectral-box inclusion or project acceptance.

**Frozen input SHA-256:** `b06319b243c861b27eb8940c09b35b5c3e13d873cfdcc6da6f7d1d928cde27ea`

**Case SHA-256:** `3ad547a3b3cc9c864d0e75591c1cab2128b532ae54989ae4260c44d2057fa949`

### GE-CHK-121 — S1 bar area centres and clear spacing

**Check:** CHK-121 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Source dimensions and longitudinal bars supplemented by a declared 8 mm tie, 20 mm aggregate and clear cover to the outer tie face.

**Normative or contract basis:** TBDY 2018 7.3.2.1 and 7.3.3; TS 500 2000 9.5.1 to 9.5.2

#### Source trace

- **GE-S05**, col1.docx; SHA-256 `75e14b85d28958e13b59e77cf12242ef6bf2546492754cd33ac9b900e45fc0de`. COL1 S1 Storey 1 longitudinal reinforcement and cover; 30/30 cm, 2.5 cm cover and 4Phi18. Original PDF pages: null; atlas pages: null. 30 by 30 cm section, cover 2.5 cm and four Phi18 bars; tie geometry is selected explicitly below

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| section | [300, 300] | mm | COL1 S1 |
| longitudinal_bars | [[4, 18]] | count / mm | COL1 S1 |
| clear_cover | 25 | mm | Benchmark cover to the outer tie face |
| tie_diameter | 8 | mm | Declared benchmark choice |
| maximum_aggregate | 20 | mm | Declared benchmark choice |
| clear_length | 2550 | mm | Declared clear length for the splice example |

#### Calculation and intermediate results

GE-CHK-121-S01: **Calculate area and ratio.**

Formula (display only): `As=4πφ²/4; ρ=As/(bh)`

Substitution: `4π18²/4; As/90000`

Result: As = 1017.8760198 mm² and rho = 0.01130973355 (units: mm²; 1)

GE-CHK-121-S02: **Locate bar centres.**

Formula (display only): `cbar=cc+φtie+φlong/2`

Substitution: `25+8+9=42`

Result: Bar centre cover = 42 mm; corner centres are at plus or minus 108 mm (units: mm)

GE-CHK-121-S03: **Calculate clear spacing.**

Formula (display only): `g=216−18; gmin=max(40,1.5φ,4dagg/3)`

Substitution: `198; max(40,27,26.6667)`

Result: Clear gap = 198 mm, exceeding the required 40 mm (units: mm)

GE-CHK-121-S04: **Locate the lap-splice zone.**

Formula (display only): `Middle third = [ln/3, 2ln/3]`

Substitution: `[850,1700] mm; selected lap interval [900,1500] mm`

Result: Middle-third interval is 850 to 1700 mm; selected splice 900 to 1500 mm fits, with splice length checked separately (units: mm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| As | 1017.8760197630929 | mm² | Independent arithmetic |
| rho | 0.011309733552923255 | 1 | Independent arithmetic |
| bar_center_offset | 108 | mm | Independent arithmetic |
| clear_gap | 198 | mm | Independent arithmetic |
| required_gap | 40 | mm | Independent arithmetic |
| splice_location_range | [850, 1700] | mm | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-121-A01 | Bar area | 1017.8760197630929 | mm² | 1e-09 | 0 |
| GE-CHK-121-A02 | Longitudinal ratio | 0.011309733552923255 | 1 | 1e-09 | 0 |
| GE-CHK-121-A03 | Clear gap | 198 | mm | 1e-09 | 0 |
| GE-CHK-121-A04 | Minimum clear gap | 40 | mm | 1e-09 | 0 |
| GE-CHK-121-A05 | Splice location | true | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-121-A05 |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Moving two bar centres to 50 mm apart gives only 32 mm clear gap, below 40 mm despite unchanged steel area. Splice interval 500 to 1100 mm violates middle-third placement.

**Report mapping:** Source 4Phi18 plus explicit cover, tie and aggregate assumptions define coordinates and pairwise gaps in LongitudinalDetailingResult. Splice location and adequate splice length are separate outputs.

**Qualification:** The source longitudinal bars are retained; actual source ties or anchorage are not verified. This area and spacing result does not replace CHK-123 or CHK-124.

**Frozen input SHA-256:** `7e73e73d4ced034820f33bd437f29cbcbc36b0277fa09de8fa10fda5b300976b`

**Case SHA-256:** `0b7db33253b56666cc9309b947e708dc5b6e0d9a389722870bc6b4e88624e71d`

### GE-CHK-122 — SB201 physical confinement-region lengths

**Check:** CHK-122 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Normal 600 by 600 mm column with 3900 mm between physical faces; cantilever and foundation extensions are separate branches.

**Normative or contract basis:** TBDY 2018 7.3.4.1, end confinement of normal storey columns

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 72, second-basement SB201 60/60, clear length 3.90 m. Original PDF pages: [72]; atlas pages: [30]. 60 by 60 cm section and clear length 3.90 m; the zone calculation is independently derived

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| section_b_h | [600, 600] | mm | EX6 SB201 |
| clear_length | 3900 | mm | EX6 SB201 |
| coordinate_origin | 0 | mm | Declared lower physical-face origin |

#### Calculation and intermediate results

GE-CHK-122-S01: **Calculate the confinement length.**

Formula (display only): `lo=max(ln/6,1.5 max(b,h),500)`

Substitution: `max(650,900,500)`

Result: lo = max(650, 900, 500) = 900 mm (units: mm)

GE-CHK-122-S02: **Bind regions to the physical faces.**

Formula (display only): `Bottom = [0,lo]; top = [ln-lo,ln]`

Substitution: `Bottom = [0,900]; top = [3000,3900]`

Result: Lower region 0 to 900 mm; upper region 3000 to 3900 mm; middle region length 2100 mm (units: mm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| confinement_length | 900 | mm | Independent arithmetic |
| lower_region | [0, 900] | mm | Independent arithmetic |
| upper_region | [3000, 3900] | mm | Independent arithmetic |
| middle_length | 2100 | mm | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-122-A01 | Confinement length | 900 | mm | 1e-09 | 0 |
| GE-CHK-122-A02 | Middle-region length | 2100 | mm | 1e-09 | 0 |
| GE-CHK-122-A03 | Complete length coverage | 3900 | mm | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** At clear length 1500 mm, two 900 mm regions overlap. Their union confines all 1500 mm; do not produce a negative middle region.

**Report mapping:** Clear length, section and physical-face identities produce ColumnConfinementRegions. Station zero has meaning only after its face mapping is established.

**Qualification:** The source supplies section and clear length; region geometry is a code-derived benchmark and does not verify captured offsets or faces.

**Frozen input SHA-256:** `1f035d92034d752f08a8cf2f4f7eea3f9e8a4f34db4629f158e1465168e107ce`

**Case SHA-256:** `f561ce589b0ef65de4cec5109f03700bdc8bc452c05b1e6f035f76ec17177d38`

### GE-CHK-123 — Detecting a missing crosstie leg in an 800 mm column

**Check:** CHK-123 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Four physical tie legs per direction at declared coordinates, checked separately from required Ash area.

**Normative or contract basis:** TBDY 2018 7.3.4.1, horizontal spacing no greater than 25 tie diameters and vertical spacing requirements

#### Source trace

- **GE-S13**, 09_KOLON_KESME_KONTROLLERI.xlsx; SHA-256 `a5e2066de1b944c8fc5b686a8ae40e02b23bbed45f46b2f7adbab564b565f811`. KOLON_ETRIYE_HESABI_TDBY2018!C6:D6 and Q6; 800 mm section and 10 mm tie. Original PDF pages: null; atlas pages: null. 800 by 800 mm section and Phi10 ties; coordinates and 90 mm spacing are new benchmark data

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| section_b_h | [800, 800] | mm | Workbook C6:D6 |
| clear_cover_tie_diameter | [40, 10] | mm | Declared cover and source diameter Q6 |
| leg_positions | [-355, -118.33333333333333, 118.33333333333333, 355] | mm | Declared physical leg coordinates |
| longitudinal_diameter_spacing | [24, 90] | mm | Declared benchmark |
| hooks_and_bar_support | Every counted leg is bound to a closed tie or suitable crosstie and the identity of its supported longitudinal bar | definition | Each counted leg is bound to a closed tie or suitable crosstie and supported longitudinal-bar identity |

#### Calculation and intermediate results

GE-CHK-123-S01: **Calculate tie-centre width.**

Formula (display only): `w=b−2(cc+φtie/2)`

Substitution: `800−2(40+5)`

Result: Tie-centre width = 710 mm (units: mm)

GE-CHK-123-S02: **Calculate horizontal leg spacing.**

Formula (display only): `amax=w/(4−1); alim=25φtie`

Substitution: `710/3; 25×10`

Result: Maximum intact gap = 236.666667 mm, below 250 mm (units: mm)

GE-CHK-123-S03: **Calculate vertical spacing bound.**

Formula (display only): `50≤s≤min(bmin/3,150,6φlong)`

Substitution: `50≤90≤min(266.667,150,144)`

Result: 50 mm <= 90 mm <= 144 mm (units: mm)

GE-CHK-123-S04: **Remove one intermediate leg.**

Formula (display only): `positions = [-355,+118.333,+355]`

Substitution: `max(473.333,236.667)`

Result: Missing-leg gap = 473.333333 mm, exceeding 250 mm (units: mm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| maximum_leg_gap | 236.66666666666666 | mm | Independent arithmetic |
| allowed_leg_gap | 250 | mm | Independent arithmetic |
| vertical_smax | 144 | mm | Independent arithmetic |
| removed_leg_gap | 473.3333333333333 | mm | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-123-A01 | Intact leg spacing | 236.66666666666666 | mm | 1e-09 | 0 |
| GE-CHK-123-A02 | Horizontal limit | 250 | mm | 1e-09 | 0 |
| GE-CHK-123-A03 | Vertical limit | 144 | mm | 1e-09 | 0 |
| GE-CHK-123-A04 | Missing-leg gap | 473.3333333333333 | mm | 1e-09 | 0 |
| GE-CHK-123-A05 | Missing-leg condition | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-123-A05 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Removing one crosstie and increasing a different leg diameter to preserve area still leaves the 473.333 mm gap. A vertical spacing of 145 mm also fails the 144 mm limit.

**Report mapping:** Source section and diameter plus declared bar/leg coordinates produce directional adjacent-leg gaps and bar support relationships in TransverseTopologyResult. Total steel area cannot conceal a topology failure.

**Qualification:** The workbook does not provide actual crosstie coordinates; this topology is an independent benchmark. Hooks, bends, corner support and attachment require their own evidence.

**Frozen input SHA-256:** `b88b308b87380dfbeffb99b66d3fbf652e65aa80a5bf9b7820329c5137a3ee8a`

**Case SHA-256:** `833a1b8de45efd0af8ce04f6f104cb308ebaa79c76aec94663279437e4161c9f`

### GE-CHK-124 — Column confinement area with five 10 mm legs

**Check:** CHK-124 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Unreduced Eq. 7.1 area and the source-provided five-leg area; the low-axial-load reduction is separate.

**Normative or contract basis:** TBDY 2018 7.3.4.1 Eq. 7.1; independently establish the two-thirds reduction branch

#### Source trace

- **GE-S13**, 09_KOLON_KESME_KONTROLLERI.xlsx; SHA-256 `a5e2066de1b944c8fc5b686a8ae40e02b23bbed45f46b2f7adbab564b565f811`. KOLON_ETRIYE_HESABI_TDBY2018!F4 and E6:W6. Original PDF pages: null; atlas pages: null. Spacing 10 cm, Ac = 6400 cm², Ack = 5184 cm², bk = 72 cm, strength ratio 3569.02/50986 = 0.07, two Ash demands and five Phi10 legs

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| spacing | 10 | cm | F4 |
| gross_and_core_area | [6400, 5184] | cm² | G6:H6 |
| core_width | 72 | cm | I6:J6 |
| strength_ratio | 0.07 | 1 | E6/F6 = 3569.02/50986 |
| leg_count_and_diameter | [5, 10] | count / mm | R6 and Q6; corresponding direction U6 |

#### Calculation and intermediate results

GE-CHK-124-S01: **Calculate the first required-area expression.**

Formula (display only): `Ash1=0.30 s bk (Ac/Ack−1) fck/fywk`

Substitution: `0.30×10×72×(6400/5184−1)×0.07`

Result: Ash1 = 3.546666667 cm² (units: cm²)

GE-CHK-124-S02: **Calculate the second expression.**

Formula (display only): `Ash2=0.075 s bk fck/fywk`

Substitution: `0.075×10×72×0.07`

Result: Ash2 = 3.78 cm² (units: cm²)

GE-CHK-124-S03: **Calculate provided area in one direction.**

Formula (display only): `Ash,provided=5π(10/10)²/4`

Substitution: `5×π×1²/4`

Result: Provided = 3.926990817 cm², exceeding max(3.546666667, 3.78) cm² (units: cm²)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Ash1 | 3.546666666666666 | cm² | Independent arithmetic |
| Ash2 | 3.78 | cm² | Independent arithmetic |
| Ash_required | 3.78 | cm² | Independent arithmetic |
| Ash_provided | 3.9269908169872414 | cm² | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-124-A01 | Strength ratio | 0.07 | 1 | 1e-09 | 0 |
| GE-CHK-124-A02 | First required area | 3.546666666666666 | cm² | 1e-09 | 0 |
| GE-CHK-124-A03 | Second required area | 3.78 | cm² | 1e-09 | 0 |
| GE-CHK-124-A04 | Five-leg provided area | 3.9269908169872414 | cm² | 1e-09 | 0 |
| GE-CHK-124-A05 | Four legs fail unreduced requirement | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-124-A05 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Four 10 mm legs provide 3.141592654 cm² and fail the unreduced 3.78 cm² requirement. A qualified two-thirds branch would require 2.52 cm², but must retain Nd, Ac, fck and applicability evidence.

**Report mapping:** Workbook inputs and core geometry feed both Eq. 7.1 branches, the directional leg list and RequiredProvidedTransverseArea.

**Qualification:** The unreduced area arithmetic is reproduced. This does not approve the source axial-load reduction or physical five-leg topology. Do not count one direction leg in the other direction total.

**Frozen input SHA-256:** `a011baa548f3a08b8063ccaa2efd4521b1db27220dbc7110a87f805fe96235f3`

**Case SHA-256:** `debd99468e5a9f0565827464ee69ca6f2b736e82532349b3c00da8b74dbb7f03`

### GE-CHK-125 — Strongcol1 S8 fails the basic SCWB inequality

**Check:** CHK-125 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

One source joint, direction and selected moment-sign pair; reported capacities are not independently solved fiber capacities.

**Normative or contract basis:** TBDY 2018 7.3.5.1 Eq. 7.3, with applicable direction, sign and axial demand

#### Source trace

- **GE-S14**, strongcol1.docx; SHA-256 `66d596e98139b227b7ac6f8ce7b992ecf52d9110793b9da2624e5968d4be8f4d`. Strong Column Checks, Storey 1, Earthquake Direction 1, S8 30/30. Original PDF pages: null; atlas pages: null. Upper-column Mr = 10.96, lower-column Mr = 11.47, K107/K106 beam-face capacities 12.89 and 7.24, printed ratio 1.11 < 1.2

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| upper_column_Mr | 10.96 | source moment unit | STRONGCOL1 S8 above, Storey 2, N = 15.742 |
| lower_column_Mr | 11.47 | source moment unit | STRONGCOL1 S8 below, Storey 1, N = 30.538 |
| beam_Mr_sign_pair | [12.89, 7.24] | source moment unit | Corresponding K107 and K106 faces and signs |
| required_factor | 1.2 | 1 | TBDY 7.3.5.1 |

#### Calculation and intermediate results

GE-CHK-125-S01: **Sum column and beam capacities.**

Formula (display only): `ΣMrc=10.96+11.47; ΣMrb=12.89+7.24`

Substitution: `22.43; 20.13`

Result: Column sum = 22.43 and beam sum = 20.13 in the source moment unit (units: source moment unit)

GE-CHK-125-S02: **Apply the SCWB inequality.**

Formula (display only): `ΣMrc≥1.2ΣMrb`

Substitution: `22.43≥24.156`

Result: 22.43 is below 1.2 times 20.13 = 24.156 (units: source moment unit; bool)

GE-CHK-125-S03: **Calculate source ratio and utilization.**

Formula (display only): `r=ΣMrc/ΣMrb; u=1.2ΣMrb/ΣMrc`

Substitution: `22.43/20.13; 24.156/22.43`

Result: Capacity ratio = 1.114257327; utilization = 1.076950513 (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| sum_column_capacity | 22.43 | source moment unit | Independent arithmetic |
| sum_beam_capacity | 20.13 | source moment unit | Independent arithmetic |
| ratio | 1.1142573273720815 | 1 | Independent arithmetic |
| utilization | 1.0769505127061971 | 1 | Independent arithmetic |
| satisfies_scwb | false | boolean | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-125-A01 | Column capacity sum | 22.43 | source moment unit | 1e-09 | 0 |
| GE-CHK-125-A02 | Beam capacity sum | 20.13 | source moment unit | 1e-09 | 0 |
| GE-CHK-125-A03 | Source capacity ratio | 1.1142573273720815 | 1 | 1e-09 | 0 |
| GE-CHK-125-A04 | SCWB utilization | 1.0769505127061971 | 1 | 1e-09 | 0 |
| GE-CHK-125-A05 | Basic SCWB criterion | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-125-A05 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** With the same beams, column sum exactly 24.156 satisfies equality. Increasing beam capacity by ten percent raises required column capacity to 26.5716 and invalidates the old result.

**Report mapping:** The incident column and beam faces and correct-sign Mr contributions produce JointSCWBResult. Source Mr cannot substitute for a new candidate capacity without its cage identity.

**Qualification:** The source failure arithmetic is reproduced. The whole-storey alpha, opposite sign and other axial states require separate evaluation with the same selected-bar revision.

**Frozen input SHA-256:** `4a96680bba8d2264a8074815b39f5fdeb71c2ecabf9d2d44b73ea947f115304c`

**Case SHA-256:** `9d0a6b6611ea5b16f53099d33fd1878fb53722f56490c1d12da25d96e4cd2d28`

### GE-CHK-126 — SB201 column capacity shear from the end mechanism

**Check:** CHK-126 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Source framed-end mechanism and distribution; the alternative amplified demand 22.16 tf does not reduce the 13.99 tf candidate.

**Normative or contract basis:** TBDY 2018 7.3.7 Eq. 7.5, with end mechanism and applicable alternative and raw-demand bounds

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 72, second-basement SB201 major-axis row. Original PDF pages: [72]; atlas pages: [30]. Clear length 3.90 m, upper Mu = 34.70 tf*m; lower sumMp = 28.99, Mha = 8.17, neighbouring Mha = 3.76 and lower Ma = 19.85 tf*m; Ve = 13.99 tf and alternative 22.16 tf

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| clear_length | 3.9 | m | EX6 SB201 |
| upper_end_Mu | 34.7 | tf·m | Reported upper-end capacity |
| beam_plastic_moment_sum | 28.99 | tf·m | Reported lower-joint sum |
| distribution_moments | [8.17, 3.76] | tf·m | Same joint and direction |
| reported_lower_end_Ma | 19.85 | tf·m | Printed lower-end value |
| alternative_D_shear | 22.16 | tf | Alternative-demand column in the same row |

#### Calculation and intermediate results

GE-CHK-126-S01: **Distribute the lower-end moment.**

Formula (display only): `Ma=ΣMp Mha/(Mha+Mha,adj)`

Substitution: `28.99×8.17/(8.17+3.76)`

Result: Unrounded Ma = 19.853168483 tf·m, printed 19.85 (units: tf*m)

GE-CHK-126-S02: **Calculate shear from both ends.**

Formula (display only): `Ve,cap=(Ma+Mu)/ln`

Substitution: `(19.85+34.70)/3.90`

Result: Capacity shear = 13.987179487 tf, printed 13.99 (units: tf)

GE-CHK-126-S03: **Compare the alternative demand.**

Formula (display only): `min(Ve,cap,V_D)`

Substitution: `min(13.987179487,22.16)`

Result: The lower of 13.987179487 and 22.16 is 13.987179487 tf; raw analysis shear remains a separate lower bound (units: tf)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Ma_unrounded | 19.85316848281643 | tf·m | Independent arithmetic |
| Ve_from_printed_ends | 13.987179487179487 | tf | Independent arithmetic |
| Ve_source | 13.99 | tf | Printed report value |
| alternative_D | 22.16 | tf | Printed report value |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-126-A01 | Lower-end distribution | 19.85316848281643 | tf·m | 1e-09 | 0 |
| GE-CHK-126-A02 | Capacity shear | 13.987179487179487 | tf | 1e-09 | 0 |
| GE-CHK-126-A03 | Printed Ve | 13.99 | tf | 1e-09 | 0 |
| GE-CHK-126-A04 | Beamless derived variant | 102.66666666666667 | kN | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** A separate beamless example with Mr = 100 and 120 kN·m and clear length 3 m gives 1.4 times their sum over length = 102.6667 kN. If raw Vd is 110 kN, final design shear is at least 110 kN.

**Report mapping:** The two end-moment origins produce joint mechanism and distribution, then ColumnCapacityShearDemand with alternative and raw-Vd comparisons.

**Qualification:** The 13.99 tf source value is Ve; 22.16 tf is an alternative demand. This page arithmetic does not establish the complete same-state raw-analysis lower bound.

**Frozen input SHA-256:** `32d6164b8cb3dfe8891855c3ddb135e10aaad65681ef2bccb665b2fe6347bbad`

**Case SHA-256:** `0e764027e60863d647e3029e21c3796d04f2bad7e2c0cf1cf260f6ef5952a807`

### GE-CHK-127 — SB201 shear resistance and separate detailing acceptance

**Check:** CHK-127 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Two source demand-to-capacity ratios and an independent small tie-contribution benchmark with Vc = 0.

**Normative or contract basis:** TBDY 2018 7.3.7.2 to 7.3.7.5; TS 500 2000 8.1.4 to 8.1.5

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 72, second-basement SB201 major axis, Ve = 13.99 tf, Vr = 90.65 tf and brittle limit = 170.91 tf. Original PDF pages: [72]; atlas pages: [30]. Ve = 13.99 tf, Vr = 90.65 tf and brittle upper limit 170.91 tf

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| source_Ve_Vr_limit | [13.99, 90.65, 170.91] | tf | Same EX6 row |
| benchmark_transverse | [4, 10, 100, 550, 365.21739130434787] | leg / mm / mm / mm / MPa | Separate four-leg 10 mm tie, spacing 100 mm, d = 550 mm, fywd = 420/1.15 MPa |
| benchmark_Vc | 0 | kN | Explicit confinement branch with earthquake-shear ratio above 0.5 and Nd <= 0.05 Ac fck |

#### Calculation and intermediate results

GE-CHK-127-S01: **Calculate source mechanical ratios.**

Formula (display only): `uVr=Ve/Vr; ulim=Ve/Vlimit`

Substitution: `13.99/90.65; 13.99/170.91`

Result: Ve/Vr = 0.154329840 and Ve/Vlimit = 0.081855948 (units: 1)

GE-CHK-127-S02: **Calculate the separate tie contribution.**

Formula (display only): `Vw=Asw fywd d/s`

Substitution: `(4π10²/4)(420/1.15)550/100`

Result: Vw = 631.050350 kN; with Vc = 0, Vr = Vw (units: kN)

GE-CHK-127-S03: **Retain detailing as an independent result.**

Formula (display only): `mechanical_ok AND transverse_detail_ok`

Substitution: `Source ratio < 1; detail_ok = False in the variant missing one crosstie leg`

Result: A missing crosstie can fail detailing despite a low mechanical ratio (units: bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| source_Vr_utilization | 0.15432984004412575 | 1 | Independent arithmetic |
| source_brittle_utilization | 0.08185594757474694 | 1 | Independent arithmetic |
| benchmark_Vw | 631.0503504167328 | kN | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-127-A01 | Source shear utilization | 0.15432984004412575 | 1 | 1e-09 | 0 |
| GE-CHK-127-A02 | Source brittle-limit utilization | 0.08185594757474694 | 1 | 1e-09 | 0 |
| GE-CHK-127-A03 | Benchmark tie contribution | 631.0503504167328 | kN | 1e-06 | 0 |
| GE-CHK-127-A04 | Detail failure remains visible | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Inherited absolute allowance 1e-06 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-127-A04 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | SPECIFIED_EXECUTABLE | GE-CHK-127-A04 |

**Narrative variant:** A demand of 91 tf exceeds Vr; 171 tf exceeds both source bounds. Unsupported longitudinal bars or excessive leg spacing must fail detailing even with unchanged mechanical utilization.

**Report mapping:** Store the two source ratios in ColumnShearResult and bind selected-tie topology separately. Do not replace EX6 Vr with the independent benchmark Vw.

**Qualification:** The source 90.65 tf capacity is reported, not independently derived from its cage. The separate Vc = 0 calculation uses its own declared reinforcement and material.

**Frozen input SHA-256:** `1d528238cad0252ed097a8013639ffc1af32e0b4822bd567eeb9e09e162039bf`

**Case SHA-256:** `a773d6b30d43c98a8298cda9011da0b9d068fbf3224189a18f4ba5346194ec66`

### GE-CHK-128 — SB201 joint panel shear and unconfined limit

**Check:** CHK-128 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

The source Ex row lists KB201 and reports As2 = 0; that row is not an independent physical connectivity census.

**Normative or contract basis:** TBDY 2018 7.5.1 to 7.5.2, Eq. 7.11; unconfined limit Vj <= bj h sqrt(fck)

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 86, second-basement SB201 Ex joint row. Original PDF pages: [86]; atlas pages: [33]. As1 = 12.06 cm², As2 = 0, column shear 11.36 tf, Ve = 53.22 tf, bj = 41.6 cm, h = 60 cm and Vmax = 139.41 tf; unconfined joint
- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 1, C30 and B420C material headings. Original PDF pages: [1]; atlas pages: [13]. C30 and B420C material family

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| As1_As2 | [1206, 0] | mm² | Source 12.06 and 0 cm² |
| fyk_fck | [420, 30] | MPa | Source material |
| column_shear | 11.36 | tf | Source Ex row |
| panel_bj_h | [416, 600] | mm | Reported effective panel dimensions |
| ton_force_conversion | 9806.65 | N/tf | N per tf conversion |

#### Calculation and intermediate results

GE-CHK-128-S01: **Calculate panel demand.**

Formula (display only): `Vj=1.25 fyk(As1+As2)−Vcol`

Substitution: `1.25×420×1206/9806.65−11.36`

Result: Vj = 53.203332 tf; the printed 53.22 tf differs within 0.05 tf rounding allowance (units: tf)

GE-CHK-128-S02: **Calculate unconfined resistance.**

Formula (display only): `Vmax=bj h sqrt(fck)`

Substitution: `416×600×sqrt(30)/9806.65`

Result: Vmax = 139.406984 tf, printed 139.41 (units: tf)

GE-CHK-128-S03: **Calculate the printed-value utilization.**

Formula (display only): `u=Ve,source/Vmax,source`

Substitution: `53.22/139.41`

Result: Source ratio = 53.22/139.41 = 0.381751668 (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Vj_from_printed_inputs | 53.20333202469753 | tf | Independent arithmetic |
| Vj_source | 53.22 | tf | Report comparison retaining differences caused by printed-input rounding |
| Vmax | 139.4069843965977 | tf | Independent arithmetic |
| utilization | 0.38175166774262964 | 1 | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-128-A01 | Panel equilibrium | 53.20333202469753 | tf | 1e-09 | 0 |
| GE-CHK-128-A02 | Rounded-source comparison | 53.22 | tf | 0.05 | 0 |
| GE-CHK-128-A03 | Unconfined capacity | 139.4069843965977 | tf | 1e-09 | 0 |
| GE-CHK-128-A04 | Source utilization | 0.38175166774262964 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. The source gives Ve = 53.22 tf with rounded steel area and column shear. The inherited 0.05 tf allowance retains the source comparison, not a code-limit margin. This does not relax an engineering acceptance limit.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Missing As2 is not zero. A verified second beam with As2 = 1206 mm² gives demand 117.766664 tf. The 1.7 enclosure coefficient requires proven four-sided enclosure.

**Report mapping:** Incident members, directional As, compatible column shear, panel dimensions and enclosure status produce JointPanelResult. Anchorage and transverse reinforcement remain separate dependent results.

**Qualification:** Equilibrium and resistance arithmetic match source precision. Reported As2 = 0 needs independent connectivity proof before physical one-sidedness is accepted; this row does not approve all signs, anchorage or ties.

**Frozen input SHA-256:** `1fc61c6dc97adc4153c77cfe7d4ee40df10a513314d3ab23f0c32b51ceedc596`

**Case SHA-256:** `18700f61b81d6987efbfa15984f0a814677c0b6b9051ba644474e106a3184124`

### GE-CHK-129 — Alpha iteration from an immutable base demand

**Check:** CHK-129 · **Kind:** CONTRACT_FIXTURE · **Population:** PRIMARY_CHECK_EXAMPLE

Rebuild absolute amplification each iteration, refresh all cage and demand dependants, and verify a true fixed point for the applicable earthquake component.

**Normative or contract basis:** Applicable TBDY 2018 7.3.6 branch and DesignIterationResult revision/convergence contract

#### Source trace

- **GE-S14**, strongcol1.docx; SHA-256 `66d596e98139b227b7ac6f8ce7b992ecf52d9110793b9da2624e5968d4be8f4d`. STRONGCOL1 Storey 1, direction 1 summary: Vs = 39.21 and Vk = 43.21; subsequent iteration values are declared fixture data. Original PDF pages: null; atlas pages: null. Vs = 39.21, Vk = 43.21 and printed 1/alpha = 1.102; 100 kNm baseline demand and second-iteration alpha are declared fixture values

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| source_Vs_Vk | [39.21, 43.21] | source shear unit | Source storey summary |
| base_earthquake_moment | 100 | kN·m | Immutable selected earthquake component with declared applicability |
| iteration2_factor | 1.05 | 1 | Assumed result from a revised candidate |
| dependent_revisions | [2, 2, 2, 2, 2] | revision | PMM, EI, SCWB, Ve and tie result revisions |

#### Calculation and intermediate results

GE-CHK-129-S01: **Calculate the first factor.**

Formula (display only): `α=Vs/Vk; f1=1/α`

Substitution: `39.21/43.21; 43.21/39.21`

Result: alpha = 0.907428836 and first factor = 1.102014792 (units: 1)

GE-CHK-129-S02: **Rebuild each demand from the base.**

Formula (display only): `M1=f1 Mbase; M2=f2 Mbase`

Substitution: `100×1.102014792; 100×1.05`

Result: Iteration 1 moment = 110.201479 kN·m; iteration 2 moment = 105 kN·m (units: kNm)

GE-CHK-129-S03: **Expose cumulative amplification error.**

Formula (display only): `Mwrong=M1 f2`

Substitution: `110.201479×1.05`

Result: Multiplying the previous demand gives the wrong 115.711553 kN·m, whereas the expected fresh-base result is 105 kNm (units: kNm)

GE-CHK-129-S04: **Record fixed-point revision requirements.**

Formula (display only): `candidate_revision and evaluated_demand_revision must agree for every consumer`

Substitution: `PMM/EI/SCWB/Ve/tie=[2,2,2,2,2]`

Result: Revision vector [2,2,2,2,2] is consistent; cage, demand and alpha stability are also checked in the same iteration (units: revision)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| alpha | 0.9074288359176117 | 1 | Independent arithmetic |
| factor1 | 1.102014792144861 | 1 | Independent arithmetic |
| M_iteration1 | 110.2014792144861 | kN·m | Independent arithmetic |
| M_iteration2 | 105 | kN·m | Independent arithmetic |
| wrong_cumulative_M | 115.71155317521041 | kN·m | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-129-A01 | Alpha ratio | 0.9074288359176117 | 1 | 1e-09 | 0 |
| GE-CHK-129-A02 | First demand | 110.2014792144861 | kN·m | 1e-09 | 0 |
| GE-CHK-129-A03 | Second absolute demand | 105 | kN·m | 1e-09 | 0 |
| GE-CHK-129-A04 | Wrong cumulative demand | 115.71155317521041 | kN·m | 1e-09 | 0 |
| GE-CHK-129-A05 | All dependent revisions match | true | bool | 0 | 0 |
| GE-CHK-129-A06 | Stale PMM revision | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-129-A05 |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-129-A06 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | SPECIFIED_EXECUTABLE | GE-CHK-129-A06 |

**Narrative variant:** A candidate sequence A to B to A is a cycle, not successful convergence. Revision vector [1,2,2,2,2] fails even if all numerical ratios are small.

**Report mapping:** Source alpha, base-demand revision and absolute factors feed PMM, EI, SCWB, Ve and ties with one cage/demand revision in DesignIterationResult. Unchanged As alone is not convergence.

**Qualification:** The first factor comes from source data; iteration values and identities are selected contract data. No global design optimum or actual engine iteration run is claimed.

**Frozen input SHA-256:** `85fcf5103eb56b08222c61caf4299dd70d2fa0e73b5e5318f49da249e458cd25`

**Case SHA-256:** `7ec088d2c7776c6c79de8d62b0ecb3fd60b412523e6e03edc2ff2ec727b2e57a`

### GE-CHK-130 — KB241 beam applicability and physical faces

**Check:** CHK-130 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Source section and clear span with explicitly selected slab and column dimensions and joint coordinates.

**Normative or contract basis:** TBDY 2018 7.4.1.1 to 7.4.1.2; physical-face and structural-role contract

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 41, second-basement KB241, b/h = 40/60 cm. Original PDF pages: [41]; atlas pages: [24]. Width 40 cm and depth 60 cm
- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 63, KB241 clear span = 7.00 m. Original PDF pages: [63]; atlas pages: [29]. Clear length 7.00 m

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| section_b_h_clear_length | [400, 600, 7000] | mm | EX6 KB241 |
| slab_thickness_column_width | [150, 300] | mm | Declared benchmark |
| joint_I_J | [[0, 0, 0], [7600, 0, 0]] | mm | Declared physical joints |
| face_offsets | [300, 300] | mm | Declared physical faces |
| Nd_fck | [0, 30] | kN / MPa | Benchmark Nd and source C30 |

#### Calculation and intermediate results

GE-CHK-130-S01: **Calculate clear span.**

Formula (display only): `ln=|J−I|−oi−oj`

Substitution: `7600−300−300`

Result: 7600 - 300 - 300 = 7000 mm (units: mm)

GE-CHK-130-S02: **Check width and depth bounds.**

Formula (display only): `bw≥250; bw≤h+bcol; h≥max(300,3tslab); h≤3.5bw`

Substitution: `400≥250;400≤900;600≥450;600≤1400`

Result: 400 >= 250; 400 <= 900; 600 >= 450; 600 <= 1400 (units: mm; bool)

GE-CHK-130-S03: **Check the deep-beam detailing trigger.**

Formula (display only): `Check h > ln/4`

Substitution: `600 > 1750 is false`

Result: 600 is not greater than 1750; this trigger does not require extra web reinforcement (units: bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| clear_length | 7000 | mm | Independent arithmetic |
| minimum_height | 450 | mm | Independent arithmetic |
| maximum_height | 1400 | mm | Independent arithmetic |
| deep_beam_trigger | false | boolean | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-130-A01 | Clear span | 7000 | mm | 1e-09 | 0 |
| GE-CHK-130-A02 | Geometry conditions | true | bool | 0 | 0 |
| GE-CHK-130-A03 | Depth trigger | false | bool | 0 | 0 |
| GE-CHK-130-A04 | Axial-role limit | 720 | kN | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-130-A02 |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Nd = 721 kN exceeds 0.1 Ac fck = 720 kN, so the ordinary beam branch cannot be assumed. Depth 1800 mm violates 3.5 bw and triggers h greater than ln/4; that second condition alone does not mean the member ceases to be a beam.

**Report mapping:** Source dimensions and benchmark face coordinates define geometry and structural role in BeamGeometryAndApplicabilityResult.

**Qualification:** Physical faces, slab and column dimensions are selected benchmark assumptions, not a validation of EX6 placement or live offsets.

**Frozen input SHA-256:** `b77391118669c79321a0c6d953b5990b960953c45e91c0c9340439f3a60abd37`

**Case SHA-256:** `b1dd2618470baa986bc2601a1fe241075fae3bddf2cdaf13243d9ff8a119ac2e`

### GE-CHK-131 — Independent rectangular flexural solution using KB241 demand

**Check:** CHK-131 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Source moment and outside dimensions with declared d = 550 mm, no flange and no compression-steel contribution.

**Normative or contract basis:** TS 500 2000 6.2.5 and 7.1, singly reinforced rectangular equilibrium benchmark

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 41, KB241 span under 1.4G + 1.6Q; Md = 22.32 tf·m and reported As = 11.00 cm². Original PDF pages: [41]; atlas pages: [24]. Md = 22.32 tf*m and b/h = 40/60; reported As = 11.00 cm² remains a separate source-reported reference
- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 1, C30 and B420C. Original PDF pages: [1]; atlas pages: [13]. C30/B420C materials

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| Md | 22.32 | tf·m | KB241 span demand |
| section_b_h_d | [400, 600, 550] | mm | Source b/h and selected d |
| fcd_fyd | [20, 365.2173913043478] | MPa | 30/1.5 and 420/1.15 |
| moment_conversion | 9806650 | N·mm/(tf·m) | 1 tf = 9806.65 N |

#### Calculation and intermediate results

GE-CHK-131-S01: **Convert moment units.**

Formula (display only): `Md=22.32×9806.65×1000`

Substitution: `22.32×9806650`

Result: Md = 218884428 N·mm (units: N*mm)

GE-CHK-131-S02: **Solve section equilibrium.**

Formula (display only): `Md=0.85fcd b a(d−a/2); a=d−sqrt(d²−2Md/(0.85fcd b))`

Substitution: `550−sqrt(550²−2×218884428/(0.85×20×400))`

Result: Compression block depth = 62.0223088513 mm (units: mm)

GE-CHK-131-S03: **Calculate required tension steel.**

Formula (display only): `As=0.85fcd b a/fyd`

Substitution: `0.85×20×400×62.0223088513/(420/1.15)`

Result: Required As = 1154.796321945 mm² = 11.547963219 cm² (units: mm²)

GE-CHK-131-S04: **Compare candidate steel area.**

Formula (display only): `As,6Φ16=6π16²/4`

Substitution: `1206.371578978≥1154.796321945`

Result: Six 16 mm bars provide 1206.371578978 mm²; area is sufficient (units: mm²; bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Md | 218884428 | N·mm | Independent arithmetic |
| a | 62.02230885129234 | mm | Independent arithmetic |
| As_required | 1154.7963219454905 | mm² | Independent arithmetic |
| source_As_reported | 11.0 | cm² | Reported using a different effective geometry or idealization; not an equality target |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-131-A01 | Moment conversion | 218884428 | N·mm | 1e-09 | 0 |
| GE-CHK-131-A02 | Compression depth | 62.02230885129234 | mm | 1e-09 | 0 |
| GE-CHK-131-A03 | Required steel area | 1154.7963219454905 | mm² | 1e-09 | 0 |
| GE-CHK-131-A04 | Candidate area condition | true | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-131-A04 |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Negative moment moves the tension face even if area is unchanged. Reducing d must increase required area. A negative square-root argument does not permit a zero or complex steel-area result.

**Report mapping:** The source moment feeds the declared rectangular section model, then a and As in BeamFlexuralDesignResult. The source 11.00 cm² remains a separately reported design with different effective geometry.

**Qualification:** This complete analytical benchmark is intentionally distinct from the source detailed idealization; the difference from 11.00 cm² is not a source-design failure or production-engine success.

**Frozen input SHA-256:** `efbe3fe76e12e83bc994f856c6f0f072798986abd917fde10aa5d5672528e5b2`

**Case SHA-256:** `303c4cdfedb66f7c3815547967d213caab1a9354bb496b3867f589e0dac48d08`

### GE-CHK-132 — KB241 top and bottom bar layout

**Check:** CHK-132 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Source bar counts and diameters with a declared 400 mm width, 30 mm clear cover, 8 mm tie and 20 mm aggregate in one layer.

**Normative or contract basis:** TS 500 2000 9.5.1 to 9.5.2; TBDY 2018 7.4.2

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 41, KB241 reinforcement column: top 4Phi14 plus 2Phi16, bottom 6Phi16. Original PDF pages: [41]; atlas pages: [24]. Four Phi14 hanger bars, two additional Phi16 top bars at each end and six straight Phi16 bottom bars; required left top area 10.15 and span area 11.00 cm²

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| section_b_h | [400, 600] | mm | EX6 KB241 |
| top_diameters | [14, 14, 16, 16, 14, 14] | mm | Source counts and diameters; selected order |
| bottom_diameters | [16, 16, 16, 16, 16, 16] | mm | Source bottom bars |
| cover_tie_aggregate | [30, 8, 20] | mm | Declared layout benchmark |
| required_top_bottom_As | [1015, 1100] | mm² | Source 10.15 and 11.00 cm² |

#### Calculation and intermediate results

GE-CHK-132-S01: **Calculate top and bottom areas.**

Formula (display only): `As,top=4A14+2A16; As,bot=6A16`

Substitution: `4π14²/4+2π16²/4; 6π16²/4`

Result: Top As = 1017.876020 mm²; bottom As = 1206.371579 mm² (units: mm²)

GE-CHK-132-S02: **Locate bottom bars and clear gaps.**

Formula (display only): `xedge=cc+φtie+φbar/2; g=(b−2xedge)/(n−1)−φbar`

Substitution: `xedge=46; g=(400−92)/5−16`

Result: Centres 46, 107.6, 169.2, 230.8, 292.4, 354 mm; clear gap = 45.6 mm (units: mm)

GE-CHK-132-S03: **Calculate equal clear gap in the mixed top row.**

Formula (display only): `g=(b−2(cc+φtie)−Σφ)/(n−1)`

Substitution: `(400−76−88)/5`

Result: Top clear gap = 47.2 mm (units: mm)

GE-CHK-132-S04: **Calculate minimum clear gap.**

Formula (display only): `gmin=max(25,φmax,4dagg/3)`

Substitution: `max(25,16,26.666667)`

Result: Required gap = 26.666667 mm; both rows satisfy it (units: mm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| As_top | 1017.8760197630929 | mm² | Independent arithmetic |
| As_bottom | 1206.3715789784806 | mm² | Independent arithmetic |
| bottom_clear_gap | 45.6 | mm | Independent arithmetic |
| top_clear_gap | 47.2 | mm | Independent arithmetic |
| minimum_clear_gap | 26.666666666666668 | mm | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-132-A01 | Top steel area | 1017.8760197630929 | mm² | 1e-09 | 0 |
| GE-CHK-132-A02 | Bottom steel area | 1206.3715789784806 | mm² | 1e-09 | 0 |
| GE-CHK-132-A03 | Bottom clear gap | 45.6 | mm | 1e-09 | 0 |
| GE-CHK-132-A04 | Top clear gap | 47.2 | mm | 1e-09 | 0 |
| GE-CHK-132-A05 | Narrow-width condition | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-132-A05 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Reducing width to 300 mm leaves bottom clear spacing 25.6 mm, below 26.6667 mm. A new multilayer candidate must be explicit; the engine cannot insert an invisible second layer.

**Report mapping:** Bar roles, candidate IDs and coordinates produce SelectedBeamCage. The same geometry revision supplies d and Mr consumers.

**Qualification:** Source bar areas are reproduced while cover and one-layer geometry are derived assumptions. Capacity still uses each tension-face effective depth.

**Frozen input SHA-256:** `ad6e7439ea8dfc8c60ac83f8d10aa645a69c153f3ec35d0f3bee0015a13a5c87`

**Case SHA-256:** `894dad919940caad8262a4d4346eae8fb8d342e94d81843e6c699ca476473a50`

### GE-CHK-133 — KB241 end-region ratios and continuous-bar identity

**Check:** CHK-133 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

A d = 550 mm end-region benchmark selecting the bottom-to-top ratio 0.5 branch for DTS 1, 2, 1a or 2a.

**Normative or contract basis:** TBDY 2018 7.4.2; TS 500 2000 7.3, Eqs. 7.3 to 7.5

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 41, KB241 assembly, straight and added top bars. Original PDF pages: [41]; atlas pages: [24]. Top end bars four Phi14 plus two Phi16, bottom six Phi16; four Phi14 hanger bars and six straight Phi16 bars are continuous-bar candidates
- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 1, C30 and B420C. Original PDF pages: [1]; atlas pages: [13]. C30/B420C materials

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| width_effective_depth | [400, 550] | mm | Source width and selected d |
| fck_fyk | [30, 420] | MPa | EX6 material |
| top_bottom_As | [1017.8760197630929, 1206.3715789784806] | mm² | Areas independently calculated from source bars |
| continuous_top_bottom_count | [4, 6] | count | Source assembly and straight bars; physical continuity is a benchmark condition |
| bottom_to_top_floor | 0.5 | 1 | Selected DTS branch |

#### Calculation and intermediate results

GE-CHK-133-S01: **Calculate minimum reinforcement.**

Formula (display only): `ρmin=0.8fctd/fyd; Asmin=ρmin bw d`

Substitution: `fctd=0.35sqrt(30)/1.5; fyd=420/1.15`

Result: rho_min = 0.002799471 and As_min = 615.883587 mm² (units: 1; mm²)

GE-CHK-133-S02: **Calculate selected end ratios.**

Formula (display only): `ρtop=As,top/(bw d); ρbot=As,bot/(bw d)`

Substitution: `1017.876020/220000;1206.371579/220000`

Result: rho_top = 0.004626709 and rho_bottom = 0.005483507, both below 0.02 (units: 1)

GE-CHK-133-S03: **Check the balanced-ratio limit.**

Formula (display only): `ρb=0.85k1 fcd/fyd × εcu/(εcu+fyd/Es)`

Substitution: `k1=0.82, fcd=20, εcu=0.003, Es=200000`

Result: rho - rho_prime <= 0.85*rho_b is checked separately and is satisfied even with rho_prime = 0 (units: 1; bool)

GE-CHK-133-S04: **Check continuous top steel area.**

Formula (display only): `As,cont,top≥0.25 max(As,end,top)`

Substitution: `4π14²/4=615.752160≥0.25×1017.876020=254.469005`

Result: Continuous top area 615.752160 mm² exceeds one quarter of end top area, 254.469005 mm² (units: mm²; bool)

GE-CHK-133-S05: **Check bottom-to-top ratio and continuous bar count.**

Formula (display only): `As,bot≥0.5As,top; ncont,top/bot≥2`

Substitution: `1206.371579 >= 508.938010; 4 >= 2 and 6 >= 2`

Result: Bottom area exceeds 508.938010 mm² and continuous counts 4 and 6 each exceed two (units: mm²; count; bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Asmin | 615.8835868835865 | mm² | Independent arithmetic |
| rho_top | 0.004626709180741331 | 1 | Independent arithmetic |
| rho_bottom | 0.005483507177174911 | 1 | Independent arithmetic |
| required_bottom_for_end_ratio | 508.9380098815464 | mm² | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-133-A01 | Minimum steel area | 615.8835868835865 | mm² | 1e-09 | 0 |
| GE-CHK-133-A02 | Top ratio | 0.004626709180741331 | 1 | 1e-09 | 0 |
| GE-CHK-133-A03 | Bottom ratio | 0.005483507177174911 | 1 | 1e-09 | 0 |
| GE-CHK-133-A04 | End-face ratio | true | bool | 0 | 0 |
| GE-CHK-133-A05 | Balanced-ratio bound | true | bool | 0 | 0 |
| GE-CHK-133-A06 | Quarter-area continuity | true | bool | 0 | 0 |
| GE-CHK-133-A07 | Removed continuity | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-133-A04, GE-CHK-133-A05, GE-CHK-133-A06 |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-133-A07 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Keeping the end area through added bars while only one top bar continues fails the continuous-bar count. Bottom As = 500 mm² fails both minimum area and the 508.938 mm² end ratio.

**Report mapping:** Bar-role identity, d and material produce min/max ratios, end-face relations and continuity tracking in BeamLongitudinalDetailingResult.

**Qualification:** This is one end-region benchmark. Other spans and faces require their own effective depths, anchorage, cut-off and continuity records.

**Frozen input SHA-256:** `79dddce8015735c31456fd6c12ac20d6f81aa65a857697243a485e9b138e0a2c`

**Case SHA-256:** `e6612923cd1d19c4c086b674db5d48a5ecc0f54f0154b2f4f223181ec27147bd`

### GE-CHK-134 — Separate positive and negative KB241 moment capacities

**Check:** CHK-134 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Declared rectangular section, d = 550 mm, no flange and no opposite-face compression-steel contribution.

**Normative or contract basis:** TS 500 2000 6.2.5 and 7.1; face-sign-capacity identity for TBDY SCWB and capacity shear

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 41, KB241 source capacities 20.27 and 23.70 tf·m and corresponding bars. Original PDF pages: [41]; atlas pages: [24]. Printed top Mr = 20.27 and bottom Mr = 23.70 tf*m; top four Phi14 plus two Phi16, bottom six Phi16. Printed Mr values remain distinct comparison labels

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| width_effective_depth | [400, 550] | mm | Source width and selected d |
| fcd_fyd | [20, 365.2173913043478] | MPa | C30/B420 with gamma_c = 1.5 and gamma_s = 1.15 |
| negative_tension_As | 1017.8760197630929 | mm² | Top 4Phi14 plus 2Phi16 |
| positive_tension_As | 1206.3715789784806 | mm² | Bottom 6Phi16 |
| face_ids | ["I_FACE", "J_FACE"] | identifier | Distinct physical faces despite equal source counts |

#### Calculation and intermediate results

GE-CHK-134-S01: **Calculate the compression block separately for each sign.**

Formula (display only): `a±=As± fyd/(0.85fcd b)`

Substitution: `Apply upper and lower areas separately`

Result: Each tension-face area produces its own block depth (units: mm)

GE-CHK-134-S02: **Calculate negative capacity.**

Formula (display only): `Mr−=As,top fyd (d−a−/2)`

Substitution: `1017.876020×365.217391×(550−a−/2)`

Result: Negative capacity = 194.298908622 kN·m (units: kNm)

GE-CHK-134-S03: **Calculate positive capacity.**

Formula (display only): `Mr+=As,bot fyd (d−a+/2)`

Substitution: `1206.371579×365.217391×(550−a+/2)`

Result: Positive capacity = 228.049975670 kN·m (units: kNm)

GE-CHK-134-S04: **Transfer capacity with its complete key.**

Formula (display only): `key=(member_id,face_id,bending_sign,cage_revision,method_id)`

Substitution: `KB241/I_FACE/NEG/CAGE-1/RECT-SINGLE; KB241/I_FACE/POS/CAGE-1/RECT-SINGLE`

Result: Retain member, face, bending sign, cage revision and method identity (units: identifier)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Mr_negative_benchmark | 194.29890862232338 | kN·m | Independent arithmetic |
| Mr_positive_benchmark | 228.0499756703097 | kN·m | Independent arithmetic |
| source_negative_Mr | 20.27 | tf·m | Source-reported value with a different detailed idealization |
| source_positive_Mr | 23.7 | tf·m | Source-reported value, not an equality target for the benchmark |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-134-A01 | Negative moment capacity | 194.29890862232338 | kN·m | 1e-09 | 0 |
| GE-CHK-134-A02 | Positive moment capacity | 228.0499756703097 | kN·m | 1e-09 | 0 |
| GE-CHK-134-A03 | Different sign capacities | true | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Removing the two added top 16 mm bars reduces negative capacity while bottom tension steel is unchanged. Submitting I/NEG under J/POS is an identity error even if the numbers coincide.

**Report mapping:** The chosen bars, coordinates and depth revision produce BeamFaceCapacityResult; SCWB and Ve consume the same face-sign-cage-method key.

**Qualification:** The benchmark does not force equality with source 20.27/23.70 tf·m. A real cage includes applicable compression bars, flange, effective depth and all bar strains for each sign.

**Frozen input SHA-256:** `e9761a92e907805f075a3589f9548c91949e30e3941b44c650e09e90e8d4a5ea`

**Case SHA-256:** `47a1204e4cf4ff2b741cd072b846d64bd3ba5944ee8ce4547f2407868366f0fb`

### GE-CHK-135 — KB201 capacity shear and the raw-demand floor

**Check:** CHK-135 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Reproduce the source capacity-shear alternatives while preserving the raw analysis-demand lower bound.

**Normative or contract basis:** TBDY 2018 7.4.5.1 Eq. 7.9 and the applicable D alternative

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 51, second-basement KB201 40/60, clear length 7.20 m. Original PDF pages: [51]; atlas pages: [25]. Clear length 7.20 m; Vdy = 12.86/16.92 tf, Mp pair 33.19 + 43.65 tf*m, capacity candidates 23.53/27.59, D alternatives 20.42/23.89, Vd = 18.54/24.39 and final Ve = 24.39 tf

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| clear_length | 7.2 | m | EX6 KB201 |
| gravity_shear_I_J | [12.86, 16.92] | tf | Source gravity-only contribution |
| plastic_moment_pair | [33.19, 43.65] | tf·m | Matching face and sign pair |
| alternative_D_shear_J | 23.89 | tf | Right-end alternative column |
| raw_shear_J | 24.39 | tf | Right-end raw design shear |
| reported_Vr | 57.11 | tf | Reported resistance |

#### Calculation and intermediate results

GE-CHK-135-S01: **Calculate the plastic-end contribution.**

Formula (display only): `ΔV=(Mpi+Mpj)/ln`

Substitution: `(33.19+43.65)/7.20`

Result: Plastic contribution = 10.672222222 tf (units: tf)

GE-CHK-135-S02: **Calculate both capacity candidates.**

Formula (display only): `Ve,I=Vdy,I+ΔV; Ve,J=Vdy,J+ΔV`

Substitution: `12.86+10.672222;16.92+10.672222`

Result: Left candidate = 23.532222222 tf; right candidate = 27.592222222 tf (units: tf)

GE-CHK-135-S03: **Apply the right-end envelope.**

Formula (display only): `Ve,J=max(Vd,J,min(Vcap,J,V_D,J))`

Substitution: `max(24.39,min(27.592222,23.89))`

Result: max(24.39, min(27.592222, 23.89)) = 24.39 tf (units: tf)

GE-CHK-135-S04: **Calculate the source resistance ratio.**

Formula (display only): `Ve/Vr`

Substitution: `24.39/57.11`

Result: Ve/Vr = 0.427070566 (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| plastic_shear_increment | 10.672222222222222 | tf | Independent arithmetic |
| capacity_candidate_I | 23.532222222222224 | tf | Independent arithmetic |
| capacity_candidate_J | 27.592222222222222 | tf | Independent arithmetic |
| design_Ve | 24.39 | tf | Independent arithmetic |
| source_Vr | 57.11 | tf | Printed report value |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-135-A01 | Plastic contribution | 10.672222222222222 | tf | 1e-09 | 0 |
| GE-CHK-135-A02 | Left capacity candidate | 23.532222222222224 | tf | 1e-09 | 0 |
| GE-CHK-135-A03 | Right capacity candidate | 27.592222222222222 | tf | 1e-09 | 0 |
| GE-CHK-135-A04 | Final design envelope | 24.39 | tf | 1e-09 | 0 |
| GE-CHK-135-A05 | Alternative removed | 27.592222222222222 | tf | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Without evidence for the D alternative, use the 27.592222 tf right-end candidate. A raw Vd = 30 tf imposes a 30 tf lower bound and cannot be reduced to 23.89.

**Report mapping:** Same-state gravity shear, correct face/sign plastic moments and clear length produce the capacity candidate, D alternative and raw-Vd floor in BeamCapacityShearDemand.

**Qualification:** The source envelope arithmetic is reproduced. Actual selected cages and the complete sign and case population remain prerequisites for member acceptance.

**Frozen input SHA-256:** `6dad50f93c11afd3fd45df0eb3624b2659a1aa524e4a82bfe8cfc53d6cec4cb8`

**Case SHA-256:** `480384e4c34ba6867526736fccc69186dae92e41122285cd3bbf88c769c6cf9c`

### GE-CHK-136 — Beam tie area spacing and four-leg geometry

**Check:** CHK-136 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Source workbook shear-steel unit check followed by a separate four-leg transverse-reinforcement benchmark.

**Normative or contract basis:** TS 500 2000 8.1.5; TBDY 2018 7.4.4 and 7.4.5

#### Source trace

- **GE-S15**, 08_KIRIS_KESME_KONTROLLERI.xlsx; SHA-256 `d061457ac341385a026b830464dc506f006f6a0ca71c92c8cc8feade344f7008`. KIRIS_KESME_KONTROL_OZET!M7:N7,R7,T7,Z7, B35 at +9.00. Original PDF pages: null; atlas pages: null. Source d = 0.67 m, Asw = 1.5707963267949 cm², spacing 0.10 m, fywd = 44335.652173913 tf/m² and Vw = 46.660327319162 tf; separate four-leg benchmark b/h = 0.60/0.70 m
- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 56, KB201 shear-reinforcement report fields. Original PDF pages: [56]; atlas pages: [26]. Report fields Ve, Vcr, Vr, Asw/s and tie description; values from the different model are not merged with the benchmark

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| benchmark_b_h_d | [600, 700, 670] | mm | Source dimensional scale; separate BENCH-BEAM-TIE |
| benchmark_fywk | 500 | MPa | Selected B500C benchmark |
| benchmark_fck | 35 | MPa | Selected C35 benchmark |
| benchmark_leg_count_diameter_spacing | [4, 10, 90] | count / mm / mm | Selected tie arrangement |
| benchmark_longitudinal_diameter_cover | [20, 30] | mm | Selected bars and clear cover |
| benchmark_Ve_Vc | [400, 0] | kN | Selected demand and qualified Vc = 0 special region |

#### Calculation and intermediate results

GE-CHK-136-S01: **Reproduce source Vw with consistent units.**

Formula (display only): `Vw=(Asw[m²]/s[m]) fywd[tf/m²] d[m]`

Substitution: `1.5707963267949×10⁻⁴/0.10×44335.652173913×0.67`

Result: Workbook Vw = 46.660327319162 tf, matching Z7 (units: tf)

GE-CHK-136-S02: **Calculate required and provided shear steel in the separate benchmark.**

Formula (display only): `(Asw/s)req=Ve/(fywd d); provided=4A10/90`

Substitution: `400000/((500/1.15)670);4π10²/(4×90)`

Result: Required Asw/s = 1.373134328 and provided = 3.490658504 mm²/mm (units: mm²/mm)

GE-CHK-136-S03: **Check minimum shear reinforcement.**

Formula (display only): `(Asw/s)min=0.3 fctd bw/fywd`

Substitution: `0.3×(0.35sqrt(35)/1.5)×600/(500/1.15)`

Result: Minimum = 0.571493307 mm²/mm, below the mechanical requirement of 1.373134328 mm²/mm (units: mm²/mm)

GE-CHK-136-S04: **Calculate tie resistance.**

Formula (display only): `Vw=Asw fywd d/s`

Substitution: `4π10²/4×(500/1.15)×670/90`

Result: Vw = 1016.843999 kN, greater than 400 kN (units: kN)

GE-CHK-136-S05: **Check confinement region and spacing.**

Formula (display only): `lo=2h; first≤50; s≤min(d/4,8φlong,150)`

Substitution: `lo=1400; first=50; s=90≤150`

Result: Confinement length = 1400 mm; first tie at 50 mm; spacing 90 mm <= 150 mm (units: mm)

GE-CHK-136-S06: **Check physical leg spacing.**

Formula (display only): `w=b−2(cc+φtie/2); maxgap=w/3`

Substitution: `(600−70)/3`

Result: Maximum leg gap = 176.666667 mm, below 350 mm (units: mm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| workbook_Vw | 46.660327319162 | tf | Recalculation of source arithmetic |
| benchmark_required_Asw_per_s | 1.373134328358209 | mm²/mm | Independent arithmetic |
| benchmark_provided_Asw_per_s | 3.490658503988659 | mm²/mm | Independent arithmetic |
| benchmark_Vw | 1016.8439989880006 | kN | Independent arithmetic |
| benchmark_confinement_length | 1400 | mm | Independent arithmetic |
| benchmark_smax | 150 | mm | Independent arithmetic |
| benchmark_max_leg_gap | 176.66666666666666 | mm | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-136-A01 | Workbook unit conversion | 46.660327319162 | tf | 1e-09 | 0 |
| GE-CHK-136-A02 | Minimum shear steel | 0.5714933070474228 | mm²/mm | 1e-09 | 0 |
| GE-CHK-136-A03 | Required shear steel | 1.373134328358209 | mm²/mm | 1e-09 | 0 |
| GE-CHK-136-A04 | Provided shear steel | 3.490658503988659 | mm²/mm | 1e-09 | 0 |
| GE-CHK-136-A05 | Tie resistance | 1016.8439989880006 | kN | 1e-09 | 0 |
| GE-CHK-136-A06 | Vertical spacing limit | 150 | mm | 1e-09 | 0 |
| GE-CHK-136-A07 | Horizontal leg gap | 176.66666666666666 | mm | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** At spacing 180 mm, resistance remains about 508.422 kN but confinement spacing fails. Reducing four legs to two gives a 530 mm horizontal gap, above 350 mm.

**Report mapping:** Source Asw, spacing, fywd and d give the workbook unit check. BENCH-BEAM-TIE separately supplies geometry, required/provided area, resistance and spacing for BeamTransverseDesignResult.

**Qualification:** Do not join values from the two source models. The EX6 notation 2Phi8 needs a drawing or topology to decide whether it means two legs or two closed ties. Hooks and supported-bar identities remain explicit inputs.

**Frozen input SHA-256:** `848af56be58d602ce3fded22396cc69a0588649578a2cd0f832a304bb7cafd2f`

**Case SHA-256:** `ef8aabb19100c92e00844646c9223e60dc9bb6c1e562f6fe40b6d6cd333550af`

### GE-CHK-137 — KB239 torsion threshold and transverse-area sum

**Check:** CHK-137 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Source negligibility and area-sum checks with a separate declared closed-tie benchmark because actual Ae and ue are not provided.

**Normative or contract basis:** TS 500 2000 8.2, Eqs. 8.11, 8.13 and 8.15 to 8.19; equilibrium or compatibility torsion must be identified

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 59, second-basement KB239: Td 6.26, Tcr 6.43 tf·m, S 0.0365 m³, shear/torsion areas and Asl. Original PDF pages: [59]; atlas pages: [27]. Td = 6.26 and Tcr = 6.43 tf*m, S = 0.0365 m³, Aov/s = 4.20, Aot/s = 5.11, Ao/s = 9.31 cm²/m and Asl = 8.54 cm²

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| Td_Tcr | [6.26, 6.43] | tf·m | EX6 KB239 |
| shear_torsion_area_per_spacing | [4.2, 5.11] | cm²/m | Same source row |
| reported_longitudinal_torsion_As | 8.54 | cm² | Same source row |
| benchmark_Ae_ue | [166400, 1680] | mm² / mm | Separate 320 by 520 mm tie-centre rectangle |
| benchmark_fywd_fyd | [365.2173913043478, 365.2173913043478] | MPa | Separate B420 design-strength benchmark |

#### Calculation and intermediate results

GE-CHK-137-S01: **Calculate the torsion negligibility threshold.**

Formula (display only): `Tignore=0.65 fctd S=(0.65/1.35)Tcr`

Substitution: `(0.65/1.35)×6.43`

Result: Threshold = 3.095925926 tf·m, below Td = 6.26; torsion cannot be neglected (units: tf*m)

GE-CHK-137-S02: **Sum source transverse areas.**

Formula (display only): `Ao/s=Aov/s+Aot/s`

Substitution: `4.20+5.11`

Result: Total transverse area = 9.31 cm²/m (units: cm²/m)

GE-CHK-137-S03: **Calculate the separate closed-tie torsion reinforcement.**

Formula (display only): `Aot/s=Td/(2Ae fywd)`

Substitution: `6.26×9806.65×1000/(2×166400×(420/1.15))`

Result: Benchmark Aot/s = 0.505080081 mm²/mm = 5.050800806 cm²/m (units: mm²/mm)

GE-CHK-137-S04: **Calculate its longitudinal torsion steel.**

Formula (display only): `Asl=(Aot/s) ue fywd/fyd`

Substitution: `0.505080081×1680`

Result: Benchmark Asl = 848.534535 mm²; do not force equality with source 8.54 cm² (units: mm²)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| source_ignore_threshold | 3.0959259259259255 | tf·m | Independent arithmetic |
| source_Ao_per_s | 9.31 | cm²/m | Independent arithmetic |
| source_Asl | 8.54 | cm² | Printed report value |
| benchmark_Aot_per_s | 0.5050800806290063 | mm²/mm | Independent arithmetic |
| benchmark_Asl | 848.5345354567306 | mm² | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-137-A01 | Negligibility threshold | 3.0959259259259255 | tf·m | 1e-09 | 0 |
| GE-CHK-137-A02 | Torsion cannot be neglected | false | bool | 0 | 0 |
| GE-CHK-137-A03 | Source transverse-area sum | 9.31 | cm²/m | 1e-09 | 0 |
| GE-CHK-137-A04 | Closed-tie torsion steel | 0.5050800806290063 | mm²/mm | 1e-09 | 0 |
| GE-CHK-137-A05 | Longitudinal torsion steel | 848.5345354567306 | mm² | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-137-A02 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Td = 3.00 tf·m lies below the threshold, whereas 6.26 cannot be replaced with zero. An internal crosstie is not part of the outer closed torsion perimeter. Existing flexural steel does not automatically eliminate torsion reinforcement.

**Report mapping:** Source Td, Tcr and S define the branch; retain shear and torsion contributions separately before their sum in BeamTorsionShearResult. Physical closed perimeter and concurrent V/T are additional inputs.

**Qualification:** The source area sum and threshold are verified. Do not copy a report check symbol as proof that its printed negligibility inequality is true. Combined V/T limits need same-cut Vd, bw, d and S.

**Frozen input SHA-256:** `96b1b523b45cf3b6a391793a46593f78122f9e3b17e2f183e43e54b04e799757`

**Case SHA-256:** `523a96ef62011d7620bb051afdbfdbd5cfae7fd8a19b1330e550fd9891271e7a`

### GE-CHK-138 — Service benchmark with cracked inertia long-term deflection and crack width

**Check:** CHK-138 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

BENCH-SVC-7200 is a declared simply supported beam at the source length scale, with unfactored service loads.

**Normative or contract basis:** TS 500 2000 13.2 Eqs. 13.1 to 13.4 and Tables 13.1 to 13.3; 13.3 Eq. 13.5 and Table 13.4

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 62, KB202, length 7.20 m and depth 60 cm; source exemption and reported crack width 0.22 mm. Original PDF pages: [62]; atlas pages: [28]. Clear length 7.20 m and depth 60 cm; reported interior-span ln/15 geometry condition and crack width 0.22 < 0.40 mm. Numerical deflection rows are absent because the source claims an exemption

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| b_h_d_L | [400, 600, 550, 7200] | mm | Declared benchmark at source h and L scale |
| As | 1206.3715789784806 | mm² | Selected six 16 mm bars |
| Ec_Es | [32000, 200000] | MPa | Declared material moduli |
| fck_fyk | [30, 420] | MPa | Selected C30/B420 |
| permanent_variable_line_load | [10, 5] | N/mm | Unfactored service loads |
| compression_ratio_duration_factor | [0, 2] | 1 | No compression bars and at least five-year factor |
| crack_cover_a_c_bar_count | [50, 50, 6] | mm / mm / count | Cover measured to tension-bar centroid, not outer clear cover |
| crack_limit | 0.4 | mm | Normal internal environment branch |

#### Calculation and intermediate results

GE-CHK-138-S01: **Calculate cracked neutral axis and inertia.**

Formula (display only): `nE=Es/Ec; bx²/2=nE As(d−x); Icr=bx³/3+nE As(d−x)²`

Substitution: `nE=6.25; As=1206.371579`

Result: x = 126.373779917 mm and Icr = 1622187797.359 mm⁴ (units: mm; mm⁴)

GE-CHK-138-S02: **Calculate cracking moment and maximum service moment.**

Formula (display only): `Ic=bh³/12; Mcr=2.5fctd Ic/(h/2); Mmax=(wG+wQ)L²/8`

Substitution: `Ic=7.2×10⁹; fctd=0.35sqrt(30)/1.5`

Result: Gross I = 7.2e9 mm⁴; Mcr = 76.681158051 kN·m; Mmax = 97.2 kN·m (units: mm⁴; N*mm)

GE-CHK-138-S03: **Calculate effective inertia.**

Formula (display only): `Ieff=(Mcr/Mmax)³ Ic+[1−(Mcr/Mmax)³] Icr`

Substitution: `r=0.490983835627`

Result: Ieff = 4360803427.017 mm⁴ with cubic weight 0.490983835627 (units: mm⁴)

GE-CHK-138-S04: **Calculate immediate and time-dependent deflection.**

Formula (display only): `δG=5wG L⁴/(384EcIeff); δQ=5wQ L⁴/(384EcIeff); λ=γt/(1+50ρ′)`

Substitution: `δG=2.507565448; δQ=1.253782724; λ=2`

Result: DeltaG = 2.507565448 mm; DeltaQ = 1.253782724 mm; long-term factor 2; total = 8.776479069 mm (units: mm; 1)

GE-CHK-138-S05: **Check selected deflection limits.**

Formula (display only): `deltaQ <= L/360; delta_t <= L/480, a deliberately conservative project limit`

Substitution: `1.253782724≤20;8.776479069≤15`

Result: Variable-load deflection is below L/360 = 20 mm; total below the selected conservative project limit L/480 = 15 mm (units: mm; bool)

GE-CHK-138-S06: **Calculate crack width.**

Formula (display only): `At=2abw/n; σs≈0.7fyd; ω=1.3(At c)^(1/3)σs×10⁻⁵`

Substitution: `At=6666.666667; c=50; σs=255.652174`

Result: At = 6666.666667 mm², steel stress = 255.652174 MPa and crack width = 0.230437112 mm, below 0.40 mm (units: mm)

GE-CHK-138-S07: **Track the separate source row.**

Formula (display only): `h > ln/15 and omega_source/omega_max`

Substitution: `600>7200/15=480;0.22/0.40`

Result: Source geometry 600 > 7200/15 = 480 is satisfied; source crack utilization is 0.22/0.40 = 0.55 (units: mm; 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| xcr | 126.37377991720257 | mm | Independent arithmetic |
| Icr | 1622187797.3592992 | mm⁴ | Independent arithmetic |
| Ieff | 4360803427.017007 | mm⁴ | Independent arithmetic |
| delta_G | 2.507565448204587 | mm | Independent arithmetic |
| delta_Q | 1.2537827241022934 | mm | Independent arithmetic |
| delta_total | 8.776479068716053 | mm | Independent arithmetic |
| omega | 0.23043711222331534 | mm | Independent arithmetic |
| source_omega | 0.22 | mm | Reported for EX6 KB202 with a different support and reinforcement model |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-138-A01 | Cracked neutral axis | 126.37377991720257 | mm | 1e-09 | 0 |
| GE-CHK-138-A02 | Cracked inertia | 1622187797.3592992 | mm⁴ | 1e-05 | 0 |
| GE-CHK-138-A03 | Effective inertia | 4360803427.017007 | mm⁴ | 1e-05 | 0 |
| GE-CHK-138-A04 | Immediate permanent-load deflection | 2.507565448204587 | mm | 1e-09 | 0 |
| GE-CHK-138-A05 | Total deflection | 8.776479068716053 | mm | 1e-09 | 0 |
| GE-CHK-138-A06 | Crack width | 0.23043711222331534 | mm | 1e-09 | 0 |
| GE-CHK-138-A07 | Source geometric condition | true | bool | 0 | 0 |
| GE-CHK-138-A08 | Wet-environment variant | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Inherited absolute allowance 1e-05 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-138-A07 |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-138-A08 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** A wet exterior limit of 0.20 mm would fail the same crack width. Replacing cracked Ieff silently with gross inertia underestimates deflection. Do not carry the source KB201 printed strict inequality at equality into this benchmark.

**Report mapping:** The separate benchmark computes xcr, Icr, Mcr, Ieff, immediate/long-term deflection and crack width in BeamServiceabilityResult. Strength combinations are not service inputs.

**Qualification:** This is a complete declared benchmark, not KB202 numerical deflection reconstruction. Source exemption depends on sensitive adjoining elements. Crack width uses the permitted approximate steel stress 0.7 fyd without a surplus-area reduction.

**Frozen input SHA-256:** `f9350cdbb69a69de99ab72ef1ccc50d8eaac6c5b05c788697d956dbe6b353960`

**Case SHA-256:** `78af1df8817604d2ed9ce41ec9b925a12d2e10b1c8404049f5f23f9456cb7b23`

### GE-CHK-139 — KB241 bottom-bar development and physical extension

**Check:** CHK-139 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

A deformed 16 mm bottom tension bar in Position II, with extension from the adjacent column face of a continuous two-sided beam.

**Normative or contract basis:** TS 500 2000 9.1.1 to 9.1.2 Eq. 9.1; TBDY 2018 7.4.3.1

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 41, KB241 bottom 6Phi16 and top additions; actual anchorage path is not published. Original PDF pages: [41]; atlas pages: [24]. Bar diameter and material family; actual anchorage polygon and length are absent from this table
- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 1, C30 and B420C. Original PDF pages: [1]; atlas pages: [13]. C30/B420C materials

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| bar_diameter | 16 | mm | EX6 KB241 |
| fck_fyk | [30, 420] | MPa | EX6 material |
| gamma_c_gamma_s | [1.5, 1.15] | 1 | Design-strength factors |
| position_factor | 1.0 | 1 | Position II for the selected lower bar |
| available_extension | 850 | mm | Declared available length along the bar from the adjacent column face |

#### Calculation and intermediate results

GE-CHK-139-S01: **Calculate design strengths.**

Formula (display only): `fctd=0.35sqrt(fck)/1.5; fyd=fyk/1.15`

Substitution: `0.35sqrt(30)/1.5;420/1.15`

Result: fctd = 1.278019301 MPa and fyd = 365.217391304 MPa (units: MPa)

GE-CHK-139-S02: **Calculate Position II development length.**

Formula (display only): `lb,II=max(0.12φ fyd/fctd,20φ)`

Substitution: `max(548.675118,320)×1.0`

Result: Position II length = 548.675118475 mm; separate Position I variant = 768.145165865 mm (units: mm)

GE-CHK-139-S03: **Apply the continuous-bottom-bar extension rule.**

Formula (display only): `lext,req=max(lb,II,50φ)`

Substitution: `max(548.675118,800)`

Result: Required extension = max(lb, 50 diameters) = 800 mm (units: mm)

GE-CHK-139-S04: **Compare actual available length.**

Formula (display only): `lavailable≥lext,req`

Substitution: `850≥800`

Result: Available 850 mm provides a 50 mm margin (units: mm; bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| lb_position_II | 548.6751184747404 | mm | Independent arithmetic |
| lb_position_I | 768.1451658646365 | mm | Independent arithmetic |
| extension_required | 800 | mm | Independent arithmetic |
| available_margin | 50 | mm | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-139-A01 | Base development length | 548.6751184747404 | mm | 1e-09 | 0 |
| GE-CHK-139-A02 | Position I length | 768.1451658646365 | mm | 1e-09 | 0 |
| GE-CHK-139-A03 | Continuity extension | 800 | mm | 1e-09 | 0 |
| GE-CHK-139-A04 | Available margin | 50 | mm | 1e-09 | 0 |
| GE-CHK-139-A05 | Short extension variant | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-139-A05 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Available extension 780 mm exceeds lb but fails the 800 mm continuity rule. Length extending into another storey or from a different face cannot be counted as available anchorage.

**Report mapping:** Source diameter and material, casting-position branch and lb lead to the continuous-bar 50-diameter requirement, then actual physical-path length in BeamAnchorageContinuityResult.

**Qualification:** Actual source anchorage geometry is absent, so this is derived. Avoid unjustified surplus-steel reductions in seismic regions. One-sided hooked ends require their separate horizontal, vertical, bend and confined-core conditions.

**Frozen input SHA-256:** `62afa3e18bcff20c8a863887c05f5fb9b3fad66d86317a7077b2f414d481a524`

**Case SHA-256:** `4c89d74d2963be403c5a30bb4af69d709b4b50cacda1d6b1c442b0ea996fd3ad`

### GE-CHK-140 — PB301 wall and analysis-component mapping

**Check:** CHK-140 · **Kind:** CONTRACT_FIXTURE · **Population:** PRIMARY_CHECK_EXAMPLE

Represent one physical cut with two shell contributions and their alternative pier aggregate without double counting.

**Normative or contract basis:** WallPierTopologyLedger physical-object and analysis-representation uniqueness

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 PDF pages 84 to 85, PB301 at third basement; shell IDs and force split are declared fixture data. Original PDF pages: [84, 85]; atlas pages: [31, 32]. PB301, storey, 30/180 section and Vd = 29.63 tf report fields; shell identities and force shares are selected for this contract example

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| physical_wall | PB301 / 3.BODRUM | identifier | EX6 page 84 |
| shell_ids | ["Shell:S-A", "Shell:S-B"] | identifier | Selected BENCH-WALLMAP mesh |
| shell_shears | [18.0, 11.63] | tf | Declared split of the 29.63 tf total |
| pier_aggregate_shear | 29.63 | tf | Fixture representation of the source total |

#### Calculation and intermediate results

GE-CHK-140-S01: **Bind the wall to two shell records.**

Formula (display only): `count(shell owners)=2`

Substitution: `S-A and S-B map to PB301`

Result: Two unique shell owners (units: count)

GE-CHK-140-S02: **Sum shell contributions at the same cut.**

Formula (display only): `Vwall=ΣV_shell`

Substitution: `18.00+11.63`

Result: Wall shear = 18.00 + 11.63 = 29.63 tf (units: tf)

GE-CHK-140-S03: **Retain the pier total as an alternative representation.**

Formula (display only): `Vphysical = Vwall; do not add Vwall + Vpier`

Substitution: `29.63; incorrect duplicate total 59.26`

Result: Physical contribution remains 29.63 tf; adding the aggregate would incorrectly give 59.26 tf (units: tf)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| wall_shear_tf | 29.63 | tf | Declared mapping example |
| double_counted_shear_tf | 59.26 | tf | Deliberately incorrect representation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-140-A01 | Shell total | 29.63 | tf | 1e-08 | 0 |
| GE-CHK-140-A02 | Incorrect double count | 59.26 | tf | 1e-08 | 0 |
| GE-CHK-140-A03 | Namespace separation | true | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-140-A03 |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Removing S-B leaves 18.00 tf but does not change the two-shell expected roster. Frame:S-A cannot replace Shell:S-A.

**Report mapping:** The PB301 source row, physical key and two shell entries reconcile with one WallCapacityShearResult input.

**Qualification:** The wall name and total come from the report. Shell IDs and the 18.00/11.63 split are selected ownership-contract data, not an ETABS acquisition.

**Frozen input SHA-256:** `9d4758ee22bd5111a6f1cec024821322145b28b5ed060c2d871dc1dc6f95895d`

**Case SHA-256:** `ad81641362d134411bcb9e8a7eeba4ffdbb5734f6a553bcb8093aa21ec8e23e4`

### GE-CHK-141 — Analytical N M point using the reported wall geometry

**Check:** CHK-141 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

PB301 geometry with two end reinforcement bundles and no web reinforcement in this selected analytical section.

**Normative or contract basis:** TS 500 2000 Chapter 7; TBDY 2018 7.6.6; declared uniaxial kernel point

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 pages 1 to 2 and 84: 300 by 1800 mm, C30/B420C and 12Phi14 per end. Original PDF pages: [1, 2, 84]; atlas pages: [13, 14, 31]. 300 by 1800 mm geometry, C30/B420C and twelve Phi14 bars at each end
- **GE-S16**, TS500.pdf; SHA-256 `d925114d01a1de2baee63738bc0da0112b547b58526c3394843c36ee66722d44`. TS500 PDF pages 28 to 29, 7.1 and Table 7.1. Original PDF pages: [28, 29]; atlas pages: null. Strain compatibility and equivalent compression-block method

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| section_b_h | [300, 1800] | mm | EX6 page 84 |
| As_each_end | 1847.2564803107985 | mm² | Twelve 14 mm bars per end |
| fcd_fyd | [20, 365.2173913043478] | MPa | Source material and design factors |
| k1_neutral_axis_depth | [0.82, 500] | 1, mm | Source k1 and selected c = 500 mm |
| end_bar_depths | [50, 1750] | mm | Declared analytical cage |
| ultimate_strain_steel_modulus | [0.003, 200000] | 1, MPa | Declared TS 500 idealization |

#### Calculation and intermediate results

GE-CHK-141-S01: **Construct block depth and bundle area.**

Formula (display only): `a=k1 c; As=12πφ²/4`

Substitution: `a=0.82×500; As=12π14²/4`

Result: a = 410 mm and As = 1847.256480 mm² per end (units: mm; mm²)

GE-CHK-141-S02: **Check yielding of both steel bundles.**

Formula (display only): `εs=εcu|1−y/c|; |σs|=min(Es εs,fyd)`

Substitution: `εsc=0.0027; εst=0.0075`

Result: Compression strain 0.0027 and tension strain 0.0075 both reach stress magnitude 365.217391 MPa (units: 1; MPa)

GE-CHK-141-S03: **Subtract concrete displaced by compression steel.**

Formula (display only): `Cc=0.85 fcd b a; Csn=As(fyd−0.85fcd); T=As fyd`

Substitution: `Cc=2091.000; Csn=643.246833; T=674.650193`

Result: Cc = 2091.000 kN, net steel compression = 643.246833 kN and tension = 674.650193 kN (units: kN)

GE-CHK-141-S04: **Sum N and M about section centre.**

Formula (display only): `N=Cc+Csn−T; M=Cc(h/2−a/2)+(Csn+T)850`

Substitution: `N=2091+643.246833−674.650193; M=(2091000×695+(643246.832644+674650.192809)×850)/10⁶`

Result: N = 2059.596640 kN and M = 2573.457472 kN·m (units: kN; kNm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| capacity_N_kN | 2059.5966398347164 | kN | Analytical strain-compatibility point |
| capacity_M_kNm | 2573.457471635083 | kNm | Analytical strain-compatibility point |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-141-A01 | Area of one end bundle | 1847.2564803107985 | mm² | 1e-08 | 0 |
| GE-CHK-141-A02 | Tension strain | 0.0075 | 1 | 1e-08 | 0 |
| GE-CHK-141-A03 | Axial capacity point | 2059.5966398347164 | kN | 1e-08 | 0 |
| GE-CHK-141-A04 | Moment capacity point | 2573.457471635083 | kN·m | 1e-08 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Omitting the compression-bar concrete subtraction overstates N by 31.403360 kN. A one-percent moment increase at the same N lies beyond this selected capacity point.

**Report mapping:** Source geometry and end bars define the explicit cage and strain/stress table, then Cc, Csn and T in WallAxialFlexuralResult. The reported PB301 demand remains a separate source row.

**Qualification:** This is a complete uniaxial reference point. It does not reproduce the real PB301 web reinforcement, biaxial demand or all detailing.

**Frozen input SHA-256:** `1e4dc52607461a35937b0f59e211c780a002dc3fd6ccecb3bc4d35472766f5e1`

**Case SHA-256:** `3b9be9b5d7e26297f8a0ff6569114510cebf5480a6dc0b12aa86e5f162a22038`

### GE-CHK-142 — PB301 critical height and boundary-zone lengths

**Check:** CHK-142 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Rectangular wall of constant length without a rigid-basement exception in the source geometry.

**Normative or contract basis:** TBDY 2018 7.6.2.1 to 7.6.2.3 and Eq. 7.15

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 1 building height and pages 84 to 85 PB301. Original PDF pages: [1, 84, 85]; atlas pages: [13, 31, 32]. Wall height 7.30 m, length 1.80 m, thickness 0.30 m and zero rigid basements
- **GE-S09**, 20180318M1-2-1.pdf; SHA-256 `8d3a9a463d4a534ec2c6834c557b5f706e2ad976c2d6837f6c9b6242e38a6bb2`. TBDY PDF page 148, critical-height and boundary-length provisions. Original PDF pages: [148]; atlas pages: null. Critical-zone and boundary-length conditions

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| wall_height | 7.3 | m | EX6 page 1 |
| wall_length | 1.8 | m | EX6 page 84 |
| wall_thickness | 0.3 | m | EX6 page 84 |

#### Calculation and intermediate results

GE-CHK-142-S01: **Calculate wall aspect ratio.**

Formula (display only): `Hw/lw`

Substitution: `7.30/1.80`

Result: Hw/lw = 4.055556, above two (units: 1)

GE-CHK-142-S02: **Determine lower and upper critical-height bounds.**

Formula (display only): `max(lw,Hw/6) ≤ Hcr ≤ 2lw`

Substitution: `max(1.80,7.30/6) ≤ Hcr ≤ 3.60`

Result: 1.80 m <= Hcr <= 3.60 m; the selected example uses the lower bound 1.80 m (units: m)

GE-CHK-142-S03: **Determine end-region lengths in critical and upper zones.**

Formula (display only): `l_end,crit=max(0.20lw,2t); l_end,upper=max(0.10lw,t)`

Substitution: `max(0.36,0.60); max(0.18,0.30)`

Result: Critical-zone end length = 0.60 m; upper-zone end length = 0.30 m (units: m)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Hw_over_lw | 4.055555555555555 | 1 | Derived from source geometry |
| Hcr_lower_m | 1.8 | m | Code lower bound |
| critical_end_length_m | 0.6 | m | Code lower bound |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-142-A01 | Wall aspect ratio | 4.055555555555555 | 1 | 1e-08 | 0 |
| GE-CHK-142-A02 | Critical-height lower bound | 1.8 | m | 1e-08 | 0 |
| GE-CHK-142-A03 | Critical end length | 0.6 | m | 1e-08 | 0 |
| GE-CHK-142-A04 | Upper-region end length | 0.3 | m | 1e-08 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** At Hw = 12.00 m, the lower critical height becomes 2.00 m while the upper bound remains 3.60 m. A rigid-basement branch changes the height reference and downward extension.

**Report mapping:** PB301 dimensions reproduce the printed aspect ratio 4.06 and produce WallCriticalBoundaryRegions.

**Qualification:** Code region dimensions are recalculated from reported geometry; installed reinforcement in those regions is not thereby proven.

**Frozen input SHA-256:** `3524c977296781e23c7e215ce1da172316ad865c846045be54236492970455bc`

**Case SHA-256:** `b291862bb9d361ed8026674ea7389690b38695b9014207ec3df129e90880dd8d`

### GE-CHK-143 — PB301 horizontal and vertical web reinforcement ratios

**Check:** CHK-143 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Separate ratios for the two faces of web reinforcement outside boundary zones.

**Normative or contract basis:** TBDY 2018 7.6.3.1 and 7.6.3.3; unreduced minimum ratio 0.0025

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 84 PB301 horizontal and web reinforcement. Original PDF pages: [84]; atlas pages: [31]. Wall thickness 300 mm, vertical Phi12/160 on both faces and horizontal Phi10/200
- **GE-S09**, 20180318M1-2-1.pdf; SHA-256 `8d3a9a463d4a534ec2c6834c557b5f706e2ad976c2d6837f6c9b6242e38a6bb2`. TBDY PDF pages 148 to 149, 7.6.3. Original PDF pages: [148, 149]; atlas pages: null. Web reinforcement ratios and spacing limits

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| wall_thickness | 300 | mm | EX6 page 84 |
| horizontal_diameter_spacing | [10, 200] | mm | Source horizontal web reinforcement |
| vertical_diameter_spacing | [12, 160] | mm | Source two-face vertical arrangement |
| minimum_ratio | 0.0025 | 1 | TBDY 7.6.3.1 |

#### Calculation and intermediate results

GE-CHK-143-S01: **Sum both horizontal faces over one metre.**

Formula (display only): `Ash/m=2(πφh²/4)(1000/sh)`

Substitution: `2(π10²/4)(1000/200)`

Result: Horizontal area = 785.398163 mm²/m (units: mm²/m)

GE-CHK-143-S02: **Calculate horizontal and vertical ratios independently.**

Formula (display only): `ρ=2(πφ²/4)/(s t)`

Substitution: `ρh=2π10²/(4×200×300); ρv=2π12²/(4×160×300)`

Result: Horizontal ratio = 0.002617994; vertical ratio = 0.004712389 (units: 1)

GE-CHK-143-S03: **Check area and spacing separately.**

Formula (display only): `ρ≥0.0025; s≤250 mm`

Substitution: `0.002617994 and 0.004712389; 200 and 160`

Result: Both ratios exceed 0.0025 and spacings 200/160 mm do not exceed 250 mm (units: 1; mm; bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| rho_horizontal | 0.0026179938779914945 | 1 | From source reinforcement |
| rho_vertical | 0.00471238898038469 | 1 | From source reinforcement |
| horizontal_provided_over_required | 1.0471975511965979 | 1 | Independent ratio |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-143-A01 | Horizontal ratio | 0.0026179938779914945 | 1 | 1e-08 | 0 |
| GE-CHK-143-A02 | Vertical ratio | 0.00471238898038469 | 1 | 1e-08 | 0 |
| GE-CHK-143-A03 | Horizontal area condition | true | bool | 0 | 0 |
| GE-CHK-143-A04 | Eight-mm counterexample | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-143-A03 |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-143-A04 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Changing horizontal bars to 8 mm at 200 mm gives ratio 0.001675516. Passing spacing cannot conceal the inadequate area.

**Report mapping:** Source bars and spacings produce separate horizontal and vertical ratio and spacing results in WallReinforcementDetailingResult.

**Qualification:** This recalculates reinforcement area and spacing. Crossties, laps and anchorage still require physical drawing linkage.

**Frozen input SHA-256:** `faf6135b58df40b45184d87341e6b3b4f328feadf961380ecc9e580bad40836f`

**Case SHA-256:** `7dfb4883a9d2c6c97a92c0faba33a9da3fd88e191b9ca24496b06c1192c03486`

### GE-CHK-144 — PB301 capacity shear and resistance comparison

**Check:** CHK-144 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Capacity-demand amplification at the base of a slender wall with the source-reported limiting branch.

**Normative or contract basis:** TBDY 2018 Eqs. 7.16 to 7.18

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 85 PB301, G+Q-Ex-0.3Ey+0.3Ez row. Original PDF pages: [85]; atlas pages: [32]. Vd, Mp, Md, beta_v, final Ve, Vr and upper limit in the same row
- **GE-S09**, 20180318M1-2-1.pdf; SHA-256 `8d3a9a463d4a534ec2c6834c557b5f706e2ad976c2d6837f6c9b6242e38a6bb2`. TBDY PDF pages 152 to 153, 7.6.6.3 to 7.6.7. Original PDF pages: [152, 153]; atlas pages: null. Capacity-shear and resistance branches

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| raw_shear | 29.63 | tf | EX6 page 85 |
| Mp_Md | [213.44, 110.23] | tfm | Same source row |
| beta_v | 1.5 | 1 | Same source row |
| limiting_shear_reported_candidate | [62.51, 86.05] | tf | Source limit lacks full gravity-earthquake decomposition |
| reported_resistance_section_limit | [184.77, 256.36] | tf | Same source row |

#### Calculation and intermediate results

GE-CHK-144-S01: **Recalculate the capacity-shear candidate.**

Formula (display only): `Ve′=βv(Mp/Md)Vd`

Substitution: `1.5×(213.44/110.23)×29.63`

Result: Candidate = 86.059519 tf; source prints 86.05 tf (units: tf)

GE-CHK-144-S02: **Apply the source-recorded limiting branch.**

Formula (display only): `Ve=min(Ve′,Ve_limit)`

Substitution: `min(86.059519,62.51)`

Result: Final Ve = min(86.059519, 62.51) = 62.51 tf (units: tf)

GE-CHK-144-S03: **Compare reinforced resistance and section upper bound separately.**

Formula (display only): `uR=Ve/Vr; umax=Ve/VeMax`

Substitution: `62.51/184.77; 62.51/256.36`

Result: Ve/Vr = 0.338312497 and Ve/VeMax = 0.243836792 (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Ve_prime_report | 86.05 | tf | Printed source with 0.02 tf comparison tolerance |
| Ve_final | 62.51 | tf | Selected branch using the source limit input |
| Ve_over_Vr | 0.3383124966174162 | 1 | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-144-A01 | Printed candidate with rounding | 86.05 | tf | 0.02 | 0 |
| GE-CHK-144-A02 | Selected shear branch | 62.51 | tf | 1e-08 | 0 |
| GE-CHK-144-A03 | Shear-resistance ratio | 0.3383124966174162 | 1 | 1e-08 | 0 |
| GE-CHK-144-A04 | Section upper-limit condition | true | bool | 0 | 0 |

**Tolerance rationale:** The source Ve-prime is 86.05 tf while the displayed inputs give approximately 86.059519 tf. The inherited 0.02 tf allowance covers this printed-input discrepancy. This does not relax an engineering acceptance limit. Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-144-A04 |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** A limiting value of 100 tf selects the 86.059519 tf candidate. A separate demand of 190 tf exceeds Vr = 184.77 tf even though it remains below the section upper limit 256.36 tf.

**Report mapping:** The same PB301 row preserves Vd, Mp/Md, candidate, limiting value, final Ve and both resistance columns in WallCapacityShearResult.

**Qualification:** Candidate arithmetic and selection from the supplied limit are reproduced. The 62.51 tf source decomposition and reinforced Vr are not independently derived.

**Frozen input SHA-256:** `817f7d51c2a94f8845a7e4a39579436bba2fb31a863e50bde34b5634fa0f3757`

**Case SHA-256:** `8278fc4a3c0c43d64781c8ad31acfb445368a81ea892e2a3e48f58a20614e62f`

### GE-CHK-145 — Normal and diagonal reinforcement branches for a coupling beam

**Check:** CHK-145 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

A separately established coupling-beam role, logical OR of the two branch conditions and a declared short high-shear diagonal design.

**Normative or contract basis:** TBDY 2018 Eqs. 7.20a and 7.20b and Eq. 7.21

#### Source trace

- **GE-S17**, ETEX_ORNEK_RAPOR.pdf; SHA-256 `4650693c95cb69860368efa5d9041a3da61b1d2aa6c5f7d26c6cb55631247f4b`. ETEX PDF page 328, B93 basement to Story 1, source geometric example. Original PDF pages: [328]; atlas pages: [38]. Width 0.50 m, depth 0.60 m, effective depth 0.56 m, clear length 2.20 m and Vd = 37.08 tf; geometry-only source example
- **GE-S09**, 20180318M1-2-1.pdf; SHA-256 `8d3a9a463d4a534ec2c6834c557b5f706e2ad976c2d6837f6c9b6242e38a6bb2`. TBDY PDF pages 153 to 154, 7.6.8.2. Original PDF pages: [153, 154]; atlas pages: null. Conventional or diagonal reinforcement branch, Asd and anchorage requirements

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| source_clear_length_depth | [2.2, 0.6] | m | ETEX page 328 B93 |
| benchmark_clear_length_depth_width_d | [1200, 600, 300, 550] | mm | Declared short coupling beam |
| shear_fctd_fyd | [400000, 1.2, 365.2173913043478] | N, MPa, MPa | Declared benchmark with fyk 420 and gamma_s 1.15 |
| diagonal_angle | 30 | degree | Declared diagonal-bundle angle |

#### Calculation and intermediate results

GE-CHK-145-S01: **Check the first branch condition using source geometry.**

Formula (display only): `ln>2h`

Substitution: `2.20>2×0.60`

Result: 2.20 m exceeds twice 0.60 m; this condition selects ordinary shear reinforcement if the member is a coupling beam (units: m; bool)

GE-CHK-145-S02: **Check both conditions for the separate short beam.**

Formula (display only): `ln > 2h or Vd <= 1.5 bw d fctd`

Substitution: `1200 > 1200 is false; 400000 <= 1.5*300*550*1.2 = 297000 is false`

Result: 1200 > 1200 is false and 400000 <= 297000 is false; diagonal reinforcement is required (units: bool)

GE-CHK-145-S03: **Calculate each diagonal-bundle area and select bars.**

Formula (display only): `Asd=Vd/(2fyd sinγ)`

Substitution: `400000/(2×365.217391×sin30°)`

Result: Required per bundle = 1095.238095 mm²; four 20 mm bars provide 1256.637061 mm² (units: mm²/bundle)

GE-CHK-145-S04: **Bind confinement and anchorage to the same selection.**

Formula (display only): `s≤min(8φ,100); l_embed≥1.5lb`

Substitution: `s <= min(160,100) = 100 mm; example Phi8/100; assuming lb = 800 mm requires l_embed >= 1200 mm`

Result: Four bars per bundle, two bundles, ties at 100 mm and embedment 1200 mm for the assumed lb = 800 mm (units: count; mm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Asd_required | 1095.2380952380952 | mm²/bundle | Analytical code benchmark |
| Asd_provided | 1256.6370614359173 | mm²/bundle | 4Φ20 |
| max_stirrup_spacing | 100 | mm | Confined diagonal-bundle branch |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-145-A01 | Source geometric branch | true | bool | 0 | 0 |
| GE-CHK-145-A02 | Short-beam normal-branch condition | false | bool | 0 | 0 |
| GE-CHK-145-A03 | Required diagonal area | 1095.2380952380952 | mm²/bundle | 1e-08 | 0 |
| GE-CHK-145-A04 | Selected diagonal area | 1256.6370614359173 | mm²/bundle | 1e-08 | 0 |
| GE-CHK-145-A05 | Bundle tie spacing | 100 | mm | 1e-08 | 0 |

**Tolerance rationale:** Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance. Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-145-A01 |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-145-A02 |
| boundary | SPECIFIED_EXECUTABLE | GE-CHK-145-A02 |
| missing_source | OPEN | None |

**Narrative variant:** At clear length 1200 mm the strict length test fails. At Vd = 297000 N, the second condition satisfies equality and the normal branch applies.

**Report mapping:** Source Lnet/H illustrates branch selection. The separate BENCH-CB-01 populates CouplingBeamDesignResult. A report label does not establish physical coupling role from geometry alone.

**Qualification:** Only B93 source geometry is reassessed. The diagonal design is a separate declared benchmark, not B93 design reconstruction.

**Frozen input SHA-256:** `b566088b3942af03b4d01df7844ca6c8c7862db8fdcf743f788380617e031de9`

**Case SHA-256:** `18eb24e496162d64fb501f64561fc4123e8351c5d6d0fc4982a1ab2b7c82f816`

### GE-CHK-146 — Same-cut storey shear share and unique contributions

**Check:** CHK-146 · **Kind:** CONTRACT_FIXTURE · **Population:** PRIMARY_CHECK_EXAMPLE

One SignedStaticState X-direction load with two walls and two frame contributions.

**Normative or contract basis:** StoryShearPartitionResult same-cut and concurrent-demand contract

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 pages 85 and 17 illustrate member/storey and direction/case fields; forces below are selected contract data. Original PDF pages: [17, 85]; atlas pages: [19, 32]. Separate member/storey and direction/case report fields; force values below are selected contract-fixture data

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| cut_key | BENCH-STORY/G1/K1/X/CUT-TOP | identifier | Selected fixture |
| wall_shears | [40, 20] | kN | Selected single loading state |
| frame_shears | [30, 10] | kN | Same fixture |
| native_storey_shear | 100 | kN | Independent total target for the fixture |

#### Calculation and intermediate results

GE-CHK-146-S01: **Prescribe the physical population.**

Formula (display only): `2 wall + 2 frame`

Substitution: `W1,W2,C1,C2`

Result: W1, W2, C1 and C2: four contributions, one direction and one case/cut (units: count)

GE-CHK-146-S02: **Sum signed forces in the same state.**

Formula (display only): `Vwall=40+20; Vframe=30+10; Vstory=Vwall+Vframe`

Substitution: `60+40`

Result: Wall 60 kN plus frame 40 kN equals 100 kN (units: kN)

GE-CHK-146-S03: **Reconcile wall share with the total.**

Formula (display only): `φ=Vwall/Vstory; r=Vstory−Vnative`

Substitution: `60/100; 100−100`

Result: Wall share = 0.60 and equilibrium residual = 0 kN (units: 1; kN)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Vwall | 60 | kN | Declared contract example |
| Vstory | 100 | kN | Declared contract example |
| phi | 0.6 | 1 | Signed contribution at the same cut |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-146-A01 | Storey shear total | 100 | kN | 1e-08 | 0 |
| GE-CHK-146-A02 | Wall shear share | 0.6 | 1 | 1e-08 | 0 |
| GE-CHK-146-A03 | Equilibrium residual | 0 | kN | 1e-08 | 0 |
| GE-CHK-146-A04 | Residual with W2 missing | -20 | kN | 1e-08 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Removing W2 gives only 80 kN without shrinking the expected denominator. Adding the same walls pier aggregate again gives 160 kN and a 60 kN imbalance.

**Report mapping:** The wall/frame contribution ledger produces one CutKey total and native-shear residual in StoryShearPartitionResult. Independent maxima are not inputs to this signed example.

**Qualification:** This complete small signed aggregation is not the actual EX6 or YENI share. Independent spectral envelopes cannot be used as concurrent signed inputs.

**Frozen input SHA-256:** `c1c944d319136ea9a505eae429602089c4ac0fc7049b0a702f711c082937ffc8`

**Case SHA-256:** `a17dd9c726b5369df14bb561d0801a4ab1f343dac1411ba707d17ee0c0853e68`

### GE-CHK-147 — Corner-joint incident roster using SB201 names

**Check:** CHK-147 · **Kind:** CONTRACT_FIXTURE · **Population:** PRIMARY_CHECK_EXAMPLE

Declared corner joint with two beams, upper and lower columns and two proven empty faces.

**Normative or contract basis:** JointTopologyFeature positive absence evidence and end-role contract

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 86 SB201: names KB201 in X and KB242 in Y; physical graph is declared separately. Original PDF pages: [86]; atlas pages: [33]. The report names KB201 in X and KB242 in Y; the physical connection topology is selected separately below

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| joint_id | BENCH-JOINT/J01 | identifier | Selected fixture |
| incident_ends | ["C_low:J", "C_up:I", "KB201:I", "KB242:I"] | end identifier | Declared directed incident roster |
| beam_directions | [[1, 0, 0], [0, 1, 0]] | unit vector | Declared global unit vectors |
| confirmed_empty_faces | ["-X", "-Y"] | face | Physical topology input, not inferred from missing results |

#### Calculation and intermediate results

GE-CHK-147-S01: **Count neighbours independently of result availability.**

Formula (display only): `nincident=ncolumn+nbeam`

Substitution: `2+2`

Result: Four incident ends (units: count)

GE-CHK-147-S02: **Check beam directions in common axes.**

Formula (display only): `dot(ex,ey)=0; |ex|=|ey|=1`

Substitution: `1×0+0×1+0×0`

Result: The beam direction vectors are orthogonal unit vectors (units: 1)

GE-CHK-147-S03: **Classify empty faces with separate evidence.**

Formula (display only): `noccupied=2; nempty=2`

Substitution: `+X and +Y occupied; -X and -Y empty`

Result: Two occupied and two empty faces define a corner, not four-sided enclosure (units: count)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| incident_end_count | 4 | count | Declared fixture topology |
| beam_face_count | 2 | count | Declared fixture topology |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-147-A01 | Incident-end count | 4 | count | 1e-08 | 0 |
| GE-CHK-147-A02 | Direction dot product | 0 | 1 | 1e-08 | 0 |
| GE-CHK-147-A03 | Four-face enclosure condition | false | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-147-A03 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | SPECIFIED_EXECUTABLE | GE-CHK-147-A03 |

**Narrative variant:** Missing KB242 force results do not change the four-end physical roster into a three-end topology. Record the missing result separately.

**Report mapping:** Add physical JointKey, incident ends and proven empty faces beside the source names. The same JointTopologyFeature roster feeds SCWB and joint shear.

**Qualification:** This is a readable connectivity fixture using source names; source As2 = 0 is not proof of an empty physical face.

**Frozen input SHA-256:** `4fd1d21e480071cb0bd6752233e4953725554bbae7eda8039ee70b18327afe5a`

**Case SHA-256:** `0650d40511599510703241381fdfb74b5fc941df5b7d0769980715ae0c3770cb`

### GE-CHK-148 — Joint reinforcement demand at the enclosure-width boundary

**Check:** CHK-148 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Centred four-beam joint whose classification and directional confinement demand change when one face becomes too narrow.

**Normative or contract basis:** TBDY 2018 7.5.1 and 7.5.2.3

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. EX6 page 86, enclosure and limit columns. Original PDF pages: [86]; atlas pages: [33]. How the report labels an unconfined joint
- **GE-S09**, 20180318M1-2-1.pdf; SHA-256 `8d3a9a463d4a534ec2c6834c557b5f706e2ad976c2d6837f6c9b6242e38a6bb2`. TBDY PDF pages 146 to 147, four faces, three-quarter width and 40/60 percent reinforcement rules. Original PDF pages: [146, 147]; atlas pages: null. Four faces, three-quarter width and 40/60 percent transverse-reinforcement requirements

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| column_b_h | [400, 600] | mm | Selected benchmark |
| beam_widths | [300, 300, 450, 450] | mm | Four centred face-closing beams |
| column_Ash_per_spacing | 0.5 | cm²/cm | Selected lower-column confinement result 5 cm² per 10 cm |
| joint_candidate | Four effective Phi8/80 legs in the checked direction | layout | First candidate with four effective 8 mm legs at 80 mm in the examined direction |

#### Calculation and intermediate results

GE-CHK-148-S01: **Check the four face-width bounds.**

Formula (display only): `bw≥0.75b_face`

Substitution: `300≥300; 450≥450`

Result: Widths 300 and 450 mm meet three-quarter equality for 400 and 600 mm faces (units: mm; bool)

GE-CHK-148-S02: **Calculate confined-joint quantity and spacing.**

Formula (display only): `(Ash/s)req=0.40×0.5; provided=(4π0.8²/4)/8`

Substitution: `0.20; 0.251327412`

Result: Required = 0.20 cm²/cm; first candidate = 0.251327412 cm²/cm and meets diameter/150 mm spacing conditions; the candidate is Phi8/80 (units: cm²/cm)

GE-CHK-148-S03: **Narrow one beam and update the classification.**

Formula (display only): `299<300; req=0.60×0.5`

Substitution: `0.30>0.251327412`

Result: A 299 mm beam makes the joint unconfined; required 0.30 exceeds 0.251327412 (units: cm²/cm)

GE-CHK-148-S04: **Select a revised candidate.**

Formula (display only): `provided=(4π1.0²/4)/10`

Substitution: `0.314159265≥0.30`

Result: Four effective 10 mm legs at 100 mm provide 0.314159265 cm²/cm and meet the unconfined spacing bound (units: cm²/cm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| confined_required_Ash_over_s | 0.2 | cm²/cm | Code benchmark |
| unconfined_required_Ash_over_s | 0.3 | cm²/cm | Code benchmark |
| revised_provided_Ash_over_s | 0.3141592653589793 | cm²/cm | 4Φ10/100 |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-148-A01 | Enclosure at width equality | true | bool | 0 | 0 |
| GE-CHK-148-A02 | Initial candidate area per spacing | 0.25132741228718347 | cm²/cm | 1e-08 | 0 |
| GE-CHK-148-A03 | Initial candidate after narrowing | false | bool | 0 | 0 |
| GE-CHK-148-A04 | Revised candidate area per spacing | 0.3141592653589793 | cm²/cm | 1e-08 | 0 |

**Tolerance rationale:** Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance. Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-148-A01 |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-148-A03 |
| boundary | SPECIFIED_EXECUTABLE | GE-CHK-148-A01 |
| missing_source | OPEN | None |

**Narrative variant:** A 449 mm beam on the other face causes the same classification change. Three sufficiently wide beams do not establish four-sided enclosure.

**Report mapping:** Geometry determines JointConfinementResult, which consumes lower-column Ash/s and produces revised amount, diameter, spacing and cage requirements.

**Qualification:** This complete declared geometric and confinement benchmark is not the actual EX6 SB201 cage design.

**Frozen input SHA-256:** `724b647a99f2719f5551ae66d6877610ba27e351b55d0db009a37b91b9c560f6`

**Case SHA-256:** `f0fd5594b602366bf44f6272a703b33c5368e39804b32b09ded06766bfcfad72`

### GE-CHK-149 — Tracing the Golden V2 D101 slab-thickness row

**Check:** CHK-149 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Conditional reproduction of the printed minimum thickness with aspect ratio and continuity stated separately.

**Normative or contract basis:** TS 500 2000 11.4.1 Eq. 11.1

#### Source trace

- **GE-S02**, 2.pdf; SHA-256 `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31`. 2.pdf page 35, printed page 33, first-storey D101. Original PDF pages: [35]; atlas pages: [10]. Thickness 15 cm, short clear span 470 cm and reported minimum thickness 11.75 cm
- **GE-S16**, TS500.pdf; SHA-256 `d925114d01a1de2baee63738bc0da0112b547b58526c3394843c36ee66722d44`. TS500 PDF pages 58 to 59, 11.4.1 to 11.4.2. Original PDF pages: [58, 59]; atlas pages: null. Two-way type and Eq. 11.1

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| provided_thickness_clear_short_span | [15, 470] | cm | Source D101 row |
| aspect_ratio_continuity | [1, 0.5] | 1 | Declared m = 1 and alpha_s = 0.5; neither is printed in the source row |
| absolute_minimum | 8 | cm | TS 500 Eq. 11.1 |

#### Calculation and intermediate results

GE-CHK-149-S01: **Bind panel identity and units.**

Formula (display only): `h=15 cm; lsn=470 cm`

Substitution: `D101 / storey 1`

Result: One panel with h = 15 cm and lsn = 470 cm (units: cm)

GE-CHK-149-S02: **Calculate thickness for the declared support scenario.**

Formula (display only): `hcalc=lsn(1−αs/4)/(15+20/m)`

Substitution: `470(1−0.5/4)/(15+20/1)`

Result: Calculated thickness = 11.75 cm (units: cm)

GE-CHK-149-S03: **Apply absolute minimum and compare provided thickness.**

Formula (display only): `hreq=max(hcalc,8); h/hreq`

Substitution: `max(11.75,8);15/11.75`

Result: Required = 11.75 cm; provided over required = 1.276595745 (units: cm; 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| reported_h_min_cm | 11.75 | cm | Printed target in Golden V2 P2_SLAB_THICKNESS_MIN |
| provided_over_required | 1.2765957446808511 | 1 | Conditional recalculation |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-149-A01 | Thickness equation | 11.75 | cm | 0.006 | 0 |
| GE-CHK-149-A02 | Required thickness | 11.75 | cm | 1e-08 | 0 |
| GE-CHK-149-A03 | Provided-to-required ratio | 1.2765957446808511 | 1 | 1e-08 | 0 |

**Tolerance rationale:** The printed thickness target is 11.75 cm. The inherited 0.006 cm allowance is retained although these declared benchmark inputs reproduce it exactly. This does not relax an engineering acceptance limit. Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** With all edges discontinuous, alpha_s = 0 and required thickness becomes 13.428571 cm. Do not copy 11.75 cm across panels without continuity evidence.

**Report mapping:** Golden V2 P2_SLAB_THICKNESS_MIN links to the D101 source row and the explicit m/alpha_s scenario in SlabGeometryAndTypeFeature.

**Qualification:** The declared m = 1 and alpha_s = 0.5 reproduce the printed target; missing source support parameters prevent an independent full D101 reconstruction.

**Frozen input SHA-256:** `5af5ebbe7afe5568418978d09a44149838681b1a3683bcc5cccbd583448a1249`

**Case SHA-256:** `78de0d37540ef8ccd936154fe1c462ae2ec1f87555c22811e8ec8c6d6919bcc9`

### GE-CHK-150 — DB212 reinforcement and an analytical strip retaining twisting moment

**Check:** CHK-150 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Reconcile required areas with actual bar diameters and spacing without mixing top support steel and bottom span steel. A separate BENCH-SLAB-TENSOR-01 retains M12 in a principal-axis transformation and a one-way reinforced concrete strip.

**Normative or contract basis:** TS 500 2000 7.1 and 11.4.2; analytical eigenvalues of the planar moment tensor

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. PDF page 27, DB212 axes 1 and 2. Original PDF pages: [27]; atlas pages: [22]. 18 cm slab; axis 1 support Md = -4.59 tfm, required As = 8.17 cm² and Phi12/13; axis 2 support required As = 5.49 cm² and Phi12/20
- **GE-S16**, TS500.pdf; SHA-256 `d925114d01a1de2baee63738bc0da0112b547b58526c3394843c36ee66722d44`. PDF pages 28 and 29, 7.1; pages 58 and 59, 11.4.2; page 67, 11.4.5. Original PDF pages: [28, 29, 58, 59, 67]; atlas pages: null. Section method, two directions and reinforcement detailing dependencies

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| M_support_x | -4.59 | tfm | EX6 page 27, DB212 axis 1 |
| As_req_x_As_req_y | [8.17, 5.49] | cm²/m | EX6 page 27 support rows |
| phi_x_s_x_phi_y_s_y | [12, 130, 12, 200] | mm | EX6 page 27 selected support bars |
| h | 180 | mm | EX6 page 27 |
| benchmark_m11_m22_m12 | [40, 20, 10] | kNm/m | Separate BENCH-SLAB-TENSOR-01, not EX6 shell results |
| benchmark_b_d_fcd_fyd | [1000, 160, 20, 365.2173913043478] | mm,mm,MPa,MPa | Analytical one-metre strip; these are not asserted as DB212 cover data |
| benchmark_rebar_direction | 22.5 | degree | Benchmark bars aligned with the principal moment direction, not the DB212 source layout |

#### Calculation and intermediate results

GE-CHK-150-S01: **Bind the tensile face to sign and source axis.**

Formula (display only): `M < 0 denotes top-support reinforcement under this example sign convention`

Substitution: `Mx=−4.59 tfm`

Result: Top face, axis 1 (units: face; axis)

GE-CHK-150-S02: **Calculate provided steel in each direction.**

Formula (display only): `As/m=(πφ²/4)(1000/s)`

Substitution: `π12²/4×1000/130; π12²/4×1000/200`

Result: 869.979504 and 565.486678 mm²/m (units: mm²/m)

GE-CHK-150-S03: **Compare each provided area with its own demand.**

Formula (display only): `As_prov≥As_req`

Substitution: `8.699795≥8.17;5.654867≥5.49`

Result: Both support-area requirements are met (units: cm²/m; bool)

GE-CHK-150-S04: **Calculate principal moments and direction with M12 retained.**

Formula (display only): `m1,2=(m11+m22)/2 ± sqrt(((m11−m22)/2)²+m12²); θ=0.5 atan2(2m12,m11−m22)`

Substitution: `30±sqrt(10²+10²); θ=22.5°`

Result: m1 = 44.142135624 and m2 = 15.857864376 kNm/m; transformed m12 = 0 (units: kNm/m; degree)

GE-CHK-150-S05: **Solve strip steel area from the stress block.**

Formula (display only): `a=d−sqrt(d²−2M/(0.85fcd b)); As=0.85fcd b a/fyd`

Substitution: `M1=44.142135624×10⁶ Nmm; b=1000,d=160,fcd=20,fyd=365.217391`

Result: a1 = 17.147602142 mm; As1 = 798.180052 and As2 = 276.510185 mm²/m (units: mm; mm²/m)

GE-CHK-150-S06: **Show resistance of the selected strip bars in those directions.**

Formula (display only): `a=As fyd/(0.85fcd b); Mr=As fyd(d−a/2)`

Substitution: `Φ12/130→As=869.979504; Φ12/200→As=565.486678`

Result: Mr1 = 47.867845600 and Mr2 = 31.789596643 kNm/m; both positive moments are resisted (units: kNm/m)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| As_provided_x | 8.699795040710196 | cm²/m | Derived from diameter and spacing |
| As_provided_y | 5.654866776461628 | cm²/m | Derived from diameter and spacing |
| provided_over_required_x | 1.0648463942117743 | 1 | Ratio to source required area |
| benchmark_principal_m1 | 44.14213562373095 | kNm/m | Analytical moment tensor |
| benchmark_As1_required | 798.180052102507 | mm²/m | Analytical rectangular compression block |
| benchmark_Mr1_selected | 47.867845599934185 | kNm/m | The same benchmark strip |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-150-A01 | Provided X area | 8.699795040710196 | cm²/m | 1e-08 | 0 |
| GE-CHK-150-A02 | Provided Y area | 5.654866776461628 | cm²/m | 1e-08 | 0 |
| GE-CHK-150-A03 | X area ratio | 1.0648463942117743 | 1 | 1e-08 | 0 |
| GE-CHK-150-A04 | Phi12/150 counterexample | false | bool | 0 | 0 |
| GE-CHK-150-A05 | Principal moment including M12 | 44.14213562373095 | kNm/m | 1e-08 | 0 |
| GE-CHK-150-A06 | Principal direction angle | 22.5 | degree | 1e-08 | 0 |
| GE-CHK-150-A07 | Analytical required As1 | 798.180052102507 | mm²/m | 1e-08 | 0 |
| GE-CHK-150-A08 | Selected strip resistance Mr1 | 47.867845599934185 | kNm/m | 1e-08 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-150-A04 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Changing X support bars to Phi12/150 reduces steel to 7.539822 cm²/m, below 8.17. Placing the same area on the lower face cannot close a top-support demand. Omitting benchmark M12 = 10 changes maximum moment from 44.142136 to 40 kNm/m and required steel from 798.180052 to 719.254881 mm²/m.

**Report mapping:** The EX6 DB212 axis, left/middle/right, Md, As and bar columns map to a face- and direction-keyed SlabFlexuralDesignResult and selected bar grid. Keep the 8.17 cm² required area separate from area derived from bar spacing. BENCH-SLAB-TENSOR-01 is a separate moment-tensor, principal-axis, strip, As and Mr chain; its moments must not be merged with the DB212 source result.

**Qualification:** The source row supports required/provided area comparison. The tensor and RC strip form an explicitly separate benchmark with bars in the principal directions. It is not a replacement for Wood-Armer or another accepted method for general shells reinforced in fixed global X/Y directions. The source Md-to-As design is not claimed to have been rerun.

**Frozen input SHA-256:** `69dba5e982caae290cbdea7366882fd31c54b88db7dbfa1fe48a70aa1635223d`

**Case SHA-256:** `d7c5446477e99c4db6943d50e4a758fa9b058366cd5a0a7734c2746d505831a6`

### GE-CHK-151 — Recalculation of SB302 punching stresses with two moments

**Check:** CHK-151 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Two-axis moment contributions at the most adverse corner of a symmetric square critical perimeter; the source example is a raft foundation slab.

**Normative or contract basis:** TBDY 2018 7.11.8 and 7.11.9, gamma_f and linear critical-perimeter stress distribution

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. PDF page 106, SB302 G-prime + Q-prime + Ey + 0.3Ex + 0.3Ez. Original PDF pages: [106]; atlas pages: [35]. d, Az, Vd, Mmaj, Mmin, c, J, gamma and stress targets
- **GE-S09**, 20180318M1-2-1.pdf; SHA-256 `8d3a9a463d4a534ec2c6834c557b5f706e2ad976c2d6837f6c9b6242e38a6bb2`. PDF pages 159 and 160, 7.11.7 to 7.11.9. Original PDF pages: [159, 160]; atlas pages: null. Moment transfer through flexure and punching

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| d | 53.5 | cm | EX6 page 106, SB302 |
| Az | 24289 | cm² | EX6 page 106 |
| Vd | 96.2 | tf | EX6 page 106 |
| Mmaj_Mmin | [22.62, 33.62] | tfm | Same EX6 page 106 row; moments already magnified by D |
| cmaj_cmin | [56.75, 56.75] | cm | EX6 page 106 |
| Jmaj_Jmin | [55046211, 55046211] | cm⁴ | EX6 page 106 |
| gamma_f | 0.6 | 1 | EX6 page 106 |
| fctd | 130.32 | tf/m² | EX6 page 106 |

#### Calculation and intermediate results

GE-CHK-151-S01: **Check the perimeter area and dimensions.**

Formula (display only): `up=Az/d; bcrit=up/4`

Substitution: `24289/53.5=454;454/4=113.5`

Result: up = 454 cm; square critical dimension 113.5 cm and c = 56.75 cm (units: cm)

GE-CHK-151-S02: **Convert shear and moment contributions to common units.**

Formula (display only): `τ0=V/Az; τM=(1−γf)(Mmaj+Mmin)c/J`

Substitution: `96.2/2.4289;0.4(22.62+33.62)0.5675/0.55046211`

Result: tau0 = 39.606406 and tauM = 23.192296 tf/m² (units: tf/m²)

GE-CHK-151-S03: **Calculate extreme corner stresses and utilization.**

Formula (display only): `τmax/min=τ0±τM; u=τmax/fctd`

Substitution: `39.606406±23.192296;62.798702/130.32`

Result: tau_max = 62.798702 and tau_min = 16.414111 tf/m²; printed targets 62.80 and 16.41 (units: tf/m²; 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| tau_max_reported | 62.8 | tf/m² | Printed target on EX6 page 106 |
| tau_min_reported | 16.41 | tf/m² | Printed target on EX6 page 106 |
| reported_ratio | 0.48189073050951503 | 1 | 62.80/130.32 |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-151-A01 | Critical perimeter | 454 | cm | 1e-08 | 0 |
| GE-CHK-151-A02 | Maximum punching stress | 62.8 | tf/m² | 0.006 | 0 |
| GE-CHK-151-A03 | Minimum punching stress | 16.41 | tf/m² | 0.006 | 0 |
| GE-CHK-151-A04 | Printed stress utilization | 0.48189073050951503 | 1 | 1e-08 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. The punching stress target is printed as 62.80 tf/m² from rounded geometric and force inputs; the retained allowance is 0.006 tf/m². This does not relax an engineering acceptance limit. The punching stress target is printed as 16.41 tf/m² from rounded geometric and force inputs; the retained allowance is 0.006 tf/m². This does not relax an engineering acceptance limit.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Ignoring moments gives only 39.606406 tf/m² and omits 23.192296 tf/m² at the critical corner. Adding an opening or free edge requires recomputing Az, c and J.

**Report mapping:** The complete EX6 page 106 SB302 row supplies perimeter geometry and J, followed by gamma_f moment transfer and the critical corner in SlabPunchingResult. Retain the raft-slab context; do not relabel it as an ordinary storey slab.

**Qualification:** The stress calculation from the same source row is reproduced within printed precision. Deriving J and the perimeter from independent model coordinates remains a separate input-verification task.

**Frozen input SHA-256:** `377993583c412389bbd2ba98f85315c1e3ce005a883e865df71289a15a9c3f0a`

**Case SHA-256:** `5613b863a850319159a99613e187e79bcbffef3d49236a516abe0e0160a2722e`

### GE-CHK-152 — DB315 deflection chain and a separate crack-width benchmark

**Check:** CHK-152 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Re-sum short- and long-term deflection components in the report and retain a separate crack-width example with declared inputs.

**Normative or contract basis:** TS 500 2000 Eq. 13.3, Table 13.3 and Eq. 13.5

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. PDF page 32, DB315(1). Original PDF pages: [32]; atlas pages: [23]. Clear span 5.40 m, instantaneous G/Q deflections 0.53/0.44 mm, additional long-term G deflection 0.93 mm, total 1.90 mm and limits
- **GE-S16**, TS500.pdf; SHA-256 `d925114d01a1de2baee63738bc0da0112b547b58526c3394843c36ee66722d44`. PDF pages 70 and 71, 13.2.3 to 13.3.2. Original PDF pages: [70, 71]; atlas pages: null. Time-dependent deflection and crack-width equations

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| ln | 5400 | mm | EX6 page 32 |
| delta_ig_delta_iq_lambda_delta_ig | [0.53, 0.44, 0.93] | mm | EX6 page 32 |
| crack_At_c_sigma_s | [6000, 25, 210] | mm²,mm,MPa | Separate BENCH-CRACK-01 assumptions; not actual DB315 inputs |
| crack_limit | 0.3 | mm | Selected indoor damp or normal outdoor exposure branch |

#### Calculation and intermediate results

GE-CHK-152-S01: **Sum the deflection components.**

Formula (display only): `δt=δig+δiq+λδig`

Substitution: `0.53+0.44+0.93`

Result: 1.90 mm (units: mm)

GE-CHK-152-S02: **Calculate the two separately selected source limits.**

Formula (display only): `δiq_lim=ln/360;δt_lim=ln/240`

Substitution: `5400/360;5400/240`

Result: 15.00 and 22.50 mm for the source-selected usage branches (units: mm)

GE-CHK-152-S03: **Fix the units in the separate crack example.**

Formula (display only): `w=1.3(At c)^(1/3)σs10⁻⁵`

Substitution: `1.3(6000×25)^(1/3)×210×10⁻⁵`

Result: w = 0.145052895 mm, below 0.30 mm (units: mm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| delta_total | 1.9 | mm | EX6 page 32 |
| instant_limit | 15 | mm | Source-selected l/360 branch |
| total_limit | 22.5 | mm | Source-selected l/240 branch |
| derived_crack_width | 0.1450528946934264 | mm | Separately declared code benchmark |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-152-A01 | Total deflection | 1.9 | mm | 1e-08 | 0 |
| GE-CHK-152-A02 | Instantaneous deflection limit | 15 | mm | 1e-08 | 0 |
| GE-CHK-152-A03 | Total deflection limit | 22.5 | mm | 1e-08 | 0 |
| GE-CHK-152-A04 | Separate crack-width benchmark | 0.1450528946934264 | mm | 1e-08 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Selecting At = 12000 mm², c = 50 mm and sigma_s = 280 MPa gives w = 0.307009490 mm, exceeding 0.30 mm. The DB315 deflection result does not replace this distinct crack-width result.

**Report mapping:** EX6 DB315(1) columns ln, delta_ig, delta_iq, lambda_delta_ig and delta_t map to SlabServiceabilityResult components. BENCH-CRACK-01 has a separate benchmark identity and demonstrates the crack-width field.

**Qualification:** The component sum and selected source limits are reproduced. This does not derive lambda from stiffness or creep inputs. Crack inputs are a declared code benchmark rather than DB315 data.

**Frozen input SHA-256:** `853ca1ca384b98acc81cf84148c3d057955eaacc9d2f87ddc2cd9a290a190309`

**Case SHA-256:** `b814396098f810f0cd041af061bf1f904a010fb936880e398038ac7cd38aea64`

### GE-CHK-153 — A 750 kN diaphragm-to-wall transfer calculation

**Check:** CHK-153 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Storey lower and upper wall shears in one signed earthquake case and anchored reinforcement remaining after flexural demand.

**Normative or contract basis:** TBDY 2018 7.11.5; transfer resistance 2Asa fyd + mu Asb fyd

#### Source trace

- **GE-S09**, 20180318M1-2-1.pdf; SHA-256 `8d3a9a463d4a534ec2c6834c557b5f706e2ad976c2d6837f6c9b6242e38a6bb2`. PDF pages 158 and 159, 7.11.3 to 7.11.5 and Figure 7.15. Original PDF pages: [158, 159]; atlas pages: null. Difference of lower and upper storey-wall shears and transfer/connection-bar resistances
- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. PDF pages 2 and 92. Original PDF pages: [2, 92]; atlas pages: [14, 34]. D = 3 and separate rigid/semi-rigid earthquake-source reporting; subsequent forces are selected benchmark values

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| V_lower_V_upper | [400, 150] | kN | Declared BENCH-DIAPH-01 values on both cut sides of the same case |
| D | 3 | 1 | Selected profile coefficient, matching D = 3 on EX6 page 2 |
| Asa_each_Asb | [804.247719318987, 804.247719318987] | mm² | Four Phi16 transfer bars on each side plus a distinct four-Phi16 connection group |
| fyd_mu | [365.2173913043478, 1] | MPa,1 | B420 divided by 1.15 and the selected monolithic-construction branch |

#### Calculation and intermediate results

GE-CHK-153-S01: **Derive transfer demand from both sides of the same case.**

Formula (display only): `ΔV=D(Vlower−Vupper)`

Substitution: `3(400−150)`

Result: 750 kN (units: kN)

GE-CHK-153-S02: **Count two transfer groups and the distinct connection group.**

Formula (display only): `Asa=Asb=4π16²/4`

Substitution: `804.247719 mm² in each declared group`

Result: Steel already consumed by flexural design is excluded from these areas (units: mm²)

GE-CHK-153-S03: **Sum transfer and friction resistances.**

Formula (display only): `R=2Asa fyd+μAsb fyd`

Substitution: `(2×804.247719+1×804.247719)×365.217391/1000`

Result: 881.175762 kN resistance and 0.851135531 utilization (units: kN; 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| transfer_demand | 750 | kN | Explicit same-case benchmark |
| transfer_capacity | 881.1757620364555 | kN | Addition prescribed by the stated method |
| utilization | 0.8511355308578852 | 1 | Independent arithmetic |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-153-A01 | Transfer demand | 750 | kN | 1e-08 | 0 |
| GE-CHK-153-A02 | Area of each bar group | 804.247719318987 | mm² | 1e-08 | 0 |
| GE-CHK-153-A03 | Transfer resistance | 881.1757620364555 | kN | 1e-08 | 0 |
| GE-CHK-153-A04 | Transfer utilization | 0.8511355308578852 | 1 | 1e-08 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** If the four Phi16 connection bars are already consumed by flexural design, Asb = 0 and resistance falls to 587.450508 kN, below 750 kN. If source forces already include D, do not multiply by 3 again.

**Report mapping:** Lower/upper WallCutState produces deltaV, followed by the inventory of available transfer and connection bars, then DiaphragmTransferResult. Show the two Asa arms and one Asb interface corresponding to Figure 7.15 separately.

**Qualification:** This is a complete small transfer-resistance example. Shell stresses, chord and collector shear friction, and actual anchorage drawings are additional design dependencies. It is not presented as a result for the source building.

**Frozen input SHA-256:** `d1dcac31b72fc7b14eb67dcfb04fa28fcd257f172fbddf3ebf89bb2516d71c6d`

**Case SHA-256:** `e90e7f07a0b4578f53f3a612773f6a98fa12be83403c90543e024a9b92a27b5b`

### GE-CHK-154 — Unit-linked foundation and P14 loaded-footprint geometry

**Check:** CHK-154 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Build common geometry in the separate foundation model while keeping the physical wall footprint, overall slab thickness and effective depth distinct.

**Normative or contract basis:** FoundationGeometryFeature; TS 500 foundation critical-section geometry

#### Source trace

- **GE-S18**, Hesap_rapor.pdf; SHA-256 `0687b4798a6c10b0a876bfc77f8789eab0a7b356fe4afae4f29ec3de10aed812`. PDF pages 115 and 116, printed pages 113 and 114, P14(50/300). Original PDF pages: [115, 116]; atlas pages: [39, 40]. Raft thickness 150 cm, P14 footprint 50 by 300 cm, effective depth 140 cm and BX3/BY5 grid intersection

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| foundation_h | 150 | cm | EUAAS page 115 |
| column_b_column_h | [50, 300] | cm | EUAAS page 116, P14 |
| effective_d | 140 | cm | EUAAS page 116 |
| location | BX3–BX3 / BY5–BY5 | grid | EUAAS page 116, grid intersection |

#### Calculation and intermediate results

GE-CHK-154-S01: **Convert all lengths to domain units.**

Formula (display only): `cm×10→mm`

Substitution: `1500,500,3000,1400`

Result: Overall h and effective d remain distinct (units: mm)

GE-CHK-154-S02: **Calculate the loaded wall footprint.**

Formula (display only): `Ac=b h`

Substitution: `0.50×3.00`

Result: 1.50 m² (units: m²)

GE-CHK-154-S03: **Derive dimensions of the interior critical rectangle.**

Formula (display only): `Bcrit=b+d;Lcrit=h+d`

Substitution: `0.50+1.40;3.00+1.40`

Result: 1.90 by 4.40 m (units: m)

GE-CHK-154-S04: **Record the effective-depth difference.**

Formula (display only): `hfoundation−d`

Substitution: `150−140`

Result: 10 cm; this difference alone is not clear cover (units: cm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| loaded_footprint_m2 | 1.5 | m² | Source geometry |
| critical_rectangle_area_m2 | 8.36 | m² | From source dimensions |
| h_minus_d_cm | 10 | cm | Geometric difference |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-154-A01 | Loaded footprint area | 1.5 | m² | 1e-08 | 0 |
| GE-CHK-154-A02 | Critical rectangle area | 8.36 | m² | 1e-08 | 0 |
| GE-CHK-154-A03 | Overall minus effective depth | 10 | cm | 1e-08 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Mistakenly using d = 150 cm gives a 9.00 m² critical area and a 13.00 m perimeter. A matching member label alone does not make that result equivalent to the original d = 140 cm calculation.

**Report mapping:** EUAAS page 115 raft definition and page 116 P14 grid, footprint and d data map to FoundationGeometryFeature, supplying the same dimensions to shear and punching checks.

**Qualification:** This recalculates dimensions and units. It does not claim to extract all foundation polygon coordinates from the source plan image.

**Frozen input SHA-256:** `41c36128ec0c5f454efc92667c7d108fb4c78513e42d9c4336b3dd0d0f818c23`

**Case SHA-256:** `956f8d3d2e7eff37d228806edcf2eb1c8cd487ffb352e86be9ad96357a2022a6`

### GE-CHK-155 — Source foundation pressure and a separate full-contact equilibrium example

**Check:** CHK-155 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Recalculate the nominal pressure-to-limit ratio in the P14 preliminary calculation and retain a separately declared full-contact benchmark under moment.

**Normative or contract basis:** FoundationSoilPressureResult requires the same geotechnical limit state and contact model

#### Source trace

- **GE-S18**, Hesap_rapor.pdf; SHA-256 `0687b4798a6c10b0a876bfc77f8789eab0a7b356fe4afae4f29ec3de10aed812`. PDF pages 115 and 116, printed pages 113 and 114. Original PDF pages: [115, 116]; atlas pages: [39, 40]. Bearing value 85.03 t/m² and P14 preliminary pressure 40 t/m²
- **GE-S18**, Hesap_rapor.pdf; SHA-256 `0687b4798a6c10b0a876bfc77f8789eab0a7b356fe4afae4f29ec3de10aed812`. PDF pages 124 and 125, printed pages 122 and 123. Original PDF pages: [124, 125]; atlas pages: [41, 42]. Stress results reported separately for each load combination

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| source_pressure | 40 | tf/m² | EUAAS page 116, p for 1.4G + 1.6Q |
| source_bearing_value | 85.03 | tf/m² | EUAAS page 115, bearing value as defined by that report |
| benchmark_N_M_B_L | [20000, 5000, 10, 10] | kN,kNm,m,m | Separate BENCH-SOIL-01 full-contact example |

#### Calculation and intermediate results

GE-CHK-155-S01: **Show the nominal ratio without deciding limit-state compatibility.**

Formula (display only): `u=p/q`

Substitution: `40/85.03`

Result: 0.470422204 (units: 1)

GE-CHK-155-S02: **Calculate area and section modulus for the separate rectangular benchmark.**

Formula (display only): `A=B L;W=B L²/6`

Substitution: `10×10;10×10²/6`

Result: 100 m² and 166.666667 m³ (units: m²; m³)

GE-CHK-155-S03: **Calculate extreme pressure and identify the contact branch.**

Formula (display only): `qmax/min=N/A±M/W`

Substitution: `20000/100±5000/166.666667`

Result: 230 and 170 kPa; both are compression (units: kPa)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| source_pressure_ratio | 0.4704222039280254 | 1 | Arithmetic of the source row |
| benchmark_qmax | 230 | kPa | Separate full-contact benchmark |
| benchmark_qmin | 170 | kPa | Separate full-contact benchmark |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-155-A01 | Source nominal ratio | 0.4704222039280254 | 1 | 1e-08 | 0 |
| GE-CHK-155-A02 | Maximum contact pressure | 230 | kPa | 1e-08 | 0 |
| GE-CHK-155-A03 | Minimum contact pressure | 170 | kPa | 1e-08 | 0 |
| GE-CHK-155-A04 | Recovered axial equilibrium | 20000 | kN | 1e-08 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Changing benchmark M to 40000 kNm gives qmin = -40 kPa. For tensionless soil, clipping the negative pressure to zero while retaining the old linear distribution is invalid; partial-contact equilibrium must be solved again.

**Report mapping:** Source p and bearing value produce a ratio retaining units and limit-state labels. Separate BENCH-SOIL-01 records contact area, qmin, qmax and axial equilibrium residual in FoundationSoilPressureResult.

**Qualification:** 40/85.03 is only the nominal ratio of two printed values. Their compatible geotechnical limit states and factors are not sufficiently established by these source rows, so the ratio is not an engineering PASS. The 230/170 kPa values belong to a separate completed contact-equilibrium benchmark rather than the source building.

**Frozen input SHA-256:** `de4a8b0e8c8c8d2c99a888c24a97f0646dbcd82150a4aec8cb62b97b67cece68`

**Case SHA-256:** `92f150a62277a4145ff9f0abf76bc345937c1a51d0d1ca2cc3e8174641dd2b3c`

### GE-CHK-156 — Subtracting soil reaction in P14 foundation punching

**Check:** CHK-156 · **Kind:** SOURCE_RECALC · **Population:** PRIMARY_CHECK_EXAMPLE

Reproduce the source TS 500 preliminary calculation for the P14 interior critical perimeter, taking gamma as the source assumption.

**Normative or contract basis:** TS 500 2000 8.3.1; Vpd = N - Fa and Vpr = gamma fctd up d

#### Source trace

- **GE-S18**, Hesap_rapor.pdf; SHA-256 `0687b4798a6c10b0a876bfc77f8789eab0a7b356fe4afae4f29ec3de10aed812`. PDF page 116, printed page 114, Figure 130. Original PDF pages: [116]; atlas pages: [40]. b = 50, h = 300 and d = 140 cm; gamma = 0.95, fctd = 13.78 kgf/cm², soil pressure 40 tf/m² and applied load 1516 tf
- **GE-S16**, TS500.pdf; SHA-256 `d925114d01a1de2baee63738bc0da0112b547b58526c3394843c36ee66722d44`. PDF pages 40 to 42, 8.3.1. Original PDF pages: [40, 41, 42]; atlas pages: null. Critical perimeter, soil reaction and punching resistance

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| b_h_d | [50, 300, 140] | cm | EUAAS page 116 |
| gamma_fctd | [0.95, 13.78] | 1,kgf/cm² | EUAAS page 116 |
| soil_p | 40 | tf/m² | EUAAS page 116 |
| N_applied | 1516 | tf | EUAAS page 116 total load labelled Vpd(Etabs) |

#### Calculation and intermediate results

GE-CHK-156-S01: **Calculate critical perimeter and enclosed area.**

Formula (display only): `up=2[(b+d)+(h+d)];Ain=(b+d)(h+d)`

Substitution: `2(190+440);1.90×4.40`

Result: up = 1260 cm and enclosed area = 8.36 m² (units: cm; m²)

GE-CHK-156-S02: **Identify the elongated loaded-area branch of Figure 8.4b.**

Formula (display only): `a1=min(h/2,3b)`

Substitution: `min(300/2,3*50) = 150 cm; a1 = h/2 in this example`

Result: The two end perimeters sum to 2(b+d) + 4(a1+d/2) = 1260 cm; retain the general h/b > 3 applicability branch (units: cm)

GE-CHK-156-S03: **Subtract soil reaction inside the perimeter.**

Formula (display only): `Fa=p Ain;Vnet=N−Fa`

Substitution: `40×8.36;1516−334.4`

Result: Fa = 334.4 tf and net demand = 1181.6 tf (units: tf)

GE-CHK-156-S04: **Calculate punching resistance in a common force unit.**

Formula (display only): `Vpr=γ fctd up d/1000`

Substitution: `0.95×13.78×1260×140/1000`

Result: 2309.2524 tf; printed 2309.25 tf (units: tf)

GE-CHK-156-S05: **Show the two equivalent demand comparisons.**

Formula (display only): `Vnet≤Vpr ↔ N≤Vpr+Fa`

Substitution: `1181.6≤2309.2524 ↔1516≤2643.6524`

Result: Net demand divided by resistance = 0.511680750 (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Fa | 334.4 | tf | Printed EUAAS target |
| Vpr | 2309.25 | tf | Printed EUAAS target |
| Nmax | 2643.65 | tf | Printed EUAAS target |
| net_demand | 1181.6 | tf | Independently calculated net demand |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-156-A01 | Critical perimeter | 1260 | cm | 1e-08 | 0 |
| GE-CHK-156-A02 | Enclosed soil reaction | 334.4 | tf | 1e-08 | 0 |
| GE-CHK-156-A03 | Punching resistance | 2309.25 | tf | 0.006 | 0 |
| GE-CHK-156-A04 | Total admissible load for the stated reaction | 2643.65 | tf | 0.006 | 0 |
| GE-CHK-156-A05 | Net punching demand | 1181.6 | tf | 1e-08 | 0 |
| GE-CHK-156-A06 | Figure 8.4b end-perimeter total | 1260 | cm | 1e-08 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. The printed punching resistance is 2309.25 tf, against 2309.2524 tf from the displayed inputs; the retained allowance is 0.006 tf. This does not relax an engineering acceptance limit. The printed total admissible load is 2643.65 tf, against 2643.6524 tf from the displayed inputs; the retained allowance is 0.006 tf. This does not relax an engineering acceptance limit.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Omitting soil reaction gives 1516 tf, overstating the net demand by 334.4 tf. With actual interior pressure p = 0, however, 1516 tf is the correct net demand. These are different scenarios.

**Report mapping:** EUAAS Figure 130 cells b, h, d, p, Fa, Vpr, Vmax and Vpd feed geometry and unit conversion, then net demand, resistance and utilization in FoundationShearPunchingResult.

**Qualification:** Printed Fa, Vpr and Vmax are reproduced. Gamma = 0.95 is adopted from the report rather than derived independently from eccentricity. This preliminary TS 500 calculation does not replace the separately reported TBDY moment-transfer stress check. The long rectangular perimeter coincides numerically with the Figure 8.4b end perimeters here, where a1 = 150 cm; a changed h/b ratio does not automatically permit the same full perimeter.

**Frozen input SHA-256:** `083f3c332382660fb988b2e38a044859bb5c8de43d42dd5f57ff1955d65436f1`

**Case SHA-256:** `3347ec484fa05d2ec38114a1cbad0729ce11136aa7931bdd849e69b1acc5da0b`

### GE-CHK-157 — From source raft reinforcement to a selected two-direction cage

**Check:** CHK-157 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Recalculate the source main-bar area, then select a cage using minimum reinforcement and flexural resistance together in a declared two-direction, single-face benchmark.

**Normative or contract basis:** TS 500 2000 7.1, 9.1.2, 10.4.3, 11.4.5 and 13.3.2; explicit gross b*h project policy for benchmark minimum areas

#### Source trace

- **GE-S18**, Hesap_rapor.pdf; SHA-256 `0687b4798a6c10b0a876bfc77f8789eab0a7b356fe4afae4f29ec3de10aed812`. PDF page 115, printed page 113, Figure 128. Original PDF pages: [115]; atlas pages: [39]. Raft thickness 150 cm and Phi25/20 main reinforcement area 24.5 cm²/m
- **GE-S16**, TS500.pdf; SHA-256 `d925114d01a1de2baee63738bc0da0112b547b58526c3394843c36ee66722d44`. PDF pages 28 and 29, 7.1; page 46, 9.1.2; page 54, 10.4.3; page 67, 11.4.5; page 71, 13.3.2. Original PDF pages: [28, 29, 46, 54, 67, 71]; atlas pages: null. Minimum ratios for the selected two-way slab branch and flexural calculation

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| source_phi_source_spacing | [25, 200] | mm | EUAAS page 115 |
| h_d | [1500, 1400] | mm | EUAAS pages 115 and 116 |
| benchmark_fcd_fyd | [20, 365.2173913043478] | MPa | C30/B420 selected for the separate benchmark, not asserted as EUAAS materials |
| benchmark_Md | 1000 | kNm/m | Declared BENCH-RAFT-REBAR-01 |
| benchmark_min_each_min_sum | [0.0015, 0.0035] | 1 | Explicit gross b*h project floors using the numerical ratios of 11.4.5, not a denominator assumption for every code branch |
| compression_phi_spacing | [16, 200] | mm | Selected upper face satisfying at least one-third of benchmark tension steel |
| net_tension_cover_free_bar_spacing | [87.5, 155] | mm | Explicit one-metre strip layout with d = 1400 mm and Phi25/180 |
| fctd_embed_provided | [1.2, 1000] | MPa,mm | Declared conservative tensile strength and Position II straight anchorage without area reduction |
| service_At_c_sigma_s | [36000, 100, 120] | mm²,mm,MPa | Separate declared service stress and bar environment; not copied from ULS moment |

#### Calculation and intermediate results

GE-CHK-157-S01: **Recalculate the source main-bar area.**

Formula (display only): `As=(πφ²/4)(1000/s)`

Substitution: `π25²/4×1000/200`

Result: 2454.369261 mm²/m = 24.543693 cm²/m; printed 24.5 (units: mm²/m; cm²/m)

GE-CHK-157-S02: **Check the same initial candidate in both benchmark directions.**

Formula (display only): `ρeach=As/(1000h);ρsum=2ρeach`

Substitution: `0.001636246;0.003272492`

Result: Individual ratio 0.0015 is satisfied; combined ratio 0.0035 is not (units: 1)

GE-CHK-157-S03: **Select the next spacing.**

Formula (display only): `Φ25/180:As=(π25²/4)(1000/180)`

Substitution: `2727.076956mm²/m;ρsum=0.003636103`

Result: Both minimum requirements are satisfied (units: mm²/m; 1)

GE-CHK-157-S04: **Evaluate flexural resistance of the same cage.**

Formula (display only): `a=As fyd/(0.85fcd b);Mr=As fyd(d−a/2)`

Substitution: `a=58.586820mm;Mr=2727.076956×365.217391×(1400−29.293410)/10⁶`

Result: Mr = 1365.190773 kNm/m exceeds Md = 1000 (units: kNm/m)

GE-CHK-157-S05: **Add compression-face steel and physical spacing.**

Formula (display only): `As_compression≥As_tension/3; clear spacing=s−φ`

Substitution: `2727.076956/3=909.025652; Φ16/200=1005.309649; 180−25=155`

Result: Compression area is sufficient; clear cover 87.5 mm and clear spacing 155 mm (units: mm²/m; mm)

GE-CHK-157-S06: **Calculate Position II straight anchorage for the selected bar.**

Formula (display only): `lb=max(0.12(fyd/fctd)φ,20φ)`

Substitution: `max(0.12×(365.217391/1.2)×25,500)`

Result: lb = 913.043478 mm; available 1000 mm is sufficient (units: mm)

GE-CHK-157-S07: **Calculate crack width using the declared service stress.**

Formula (display only): `w=1.3(At c)^(1/3)σs10⁻⁵`

Substitution: `1.3(36000×100)^(1/3)×120×10⁻⁵`

Result: 0.239088543 mm, below the selected 0.30 mm exposure limit (units: mm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| source_As_cm2_per_m | 24.54369260617026 | cm²/m | Arithmetic using source diameter and spacing |
| benchmark_selected_As | 2727.07695624114 | mm²/m | Φ25/180 |
| benchmark_Mr | 1365.1907734996707 | kNm/m | The same selected reinforcement cage |
| benchmark_compression_As | 1005.3096491487337 | mm²/m | Selected Phi16/200 |
| benchmark_lb | 913.0434782608697 | mm | Position II and fctd = 1.2 MPa |
| benchmark_service_crack | 0.23908854290678852 | mm | Declared serviceability inputs |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-157-A01 | Source main-bar area | 24.54369260617026 | cm²/m | 1e-08 | 0 |
| GE-CHK-157-A02 | Initial combined minimum fails | false | bool | 0 | 0 |
| GE-CHK-157-A03 | Selected area | 2727.07695624114 | mm²/m | 1e-08 | 0 |
| GE-CHK-157-A04 | Selected combined minimum passes | true | bool | 0 | 0 |
| GE-CHK-157-A05 | Selected flexural resistance | 1365.1907734996707 | kNm/m | 1e-08 | 0 |
| GE-CHK-157-A06 | Compression-face area | 1005.3096491487337 | mm²/m | 1e-08 | 0 |
| GE-CHK-157-A07 | Compression area at least one third | true | bool | 0 | 0 |
| GE-CHK-157-A08 | Straight anchorage length | 913.0434782608697 | mm | 1e-08 | 0 |
| GE-CHK-157-A09 | Service crack width | 0.23908854290678852 | mm | 1e-08 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-CHK-157-A04, GE-CHK-157-A07 |
| negative | SPECIFIED_EXECUTABLE | GE-CHK-157-A02 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** A demand/resistance check alone can make Phi25/200 appear sufficient in flexure while missing this benchmark combined minimum ratio. A change of steel face or anchorage requires revised capacity and serviceability results.

**Report mapping:** EUAAS Figure 128 gives actual As per metre. Separate BENCH-RAFT-REBAR-01 links two-direction minimum areas, candidate spacing and the same cage resistance to FoundationReinforcementDesignResult.

**Qualification:** Only the source 24.5 cm²/m row is verified as source arithmetic; remaining values are BENCH-RAFT-REBAR-01. Minimum areas use an explicit gross b*h project policy, and a normative denominator must be fixed separately in the method profile. Calculated Mr is a singly reinforced strip lower bound that omits any capacity benefit from compression steel. Cover, anchorage and service stress are declared inputs. Do not infer inadequacy of the actual EUAAS raft without its supplementary and upper-face steel.

**Frozen input SHA-256:** `a3f3aeb68794bd55ba13fbc3419e0e174e4e223b49a6b9d979561e4d3827579c`

**Case SHA-256:** `426e75281b8563c904ecddb89d39a2f84652cc76bb98c013d1636f2851bde110`

### GE-CHK-158 — Transferring SB301 forces and the moment reference to a foundation

**Check:** CHK-158 · **Kind:** DERIVED_BENCHMARK · **Population:** PRIMARY_CHECK_EXAMPLE

Convert a single source force vector and transport its declared global reference while retaining distinct superstructure and foundation model identities.

**Normative or contract basis:** SuperstructureFoundationTransferResult; Ftarget = R Fsource and Mtarget = R Msource + r cross Ftarget

#### Source trace

- **GE-S04**, ex_Hesap_Raporu6.pdf; SHA-256 `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9`. PDF page 92, SB301 G-prime row. Original PDF pages: [92]; atlas pages: [34]. N = -16.537 tf, M2 = 3.707 tfm and M3 = -14.742 tfm from one source row

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| source_N_M2_M3 | [-16.537, 3.707, -14.742] | tf,tfm,tfm | EX6 page 92, SB301 G-prime |
| tf_to_kN | 9.80665 | kN/tf | Defined standard tonne-force conversion |
| R | I | matrix | Declared benchmark mapping: M2 to global X, M3 to global Y and N to global Z |
| r_target_to_source | [1, 2, 0] | m | Explicit reference-transport assumption, not a source-plan coordinate |

#### Calculation and intermediate results

GE-CHK-158-S01: **Convert forces and moments from the same row.**

Formula (display only): `Fz=N×9.80665;Mx=M2×9.80665;My=M3×9.80665`

Substitution: `−16.537×9.80665;3.707×9.80665;−14.742×9.80665`

Result: Fz = -162.172571 kN; Mx = 36.353252 and My = -144.569634 kNm (units: kN; kNm)

GE-CHK-158-S02: **Calculate the moment caused by reference transport.**

Formula (display only): `r×F=(2Fz,−Fz,0)`

Substitution: `(−324.345142,+162.172571,0)`

Result: kNm (units: kNm)

GE-CHK-158-S03: **Calculate target moments and inverse-transport residual.**

Formula (display only): `Mtx=Mx+2Fz;Mty=My−Fz`

Substitution: `36.353252−324.345142;−144.569634+162.172571`

Result: Mtx = -287.991891 and Mty = 17.602937 kNm; inverse residual = 0 (units: kNm)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| Fz_kN | -162.17257105 | kN | Derived from the source vector |
| Mx_target | -287.99189055 | kNm | Declared reference transport |
| My_target | 17.602936749999998 | kNm | Declared reference transport |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-CHK-158-A01 | Converted axial force | -162.17257105 | kN | 1e-08 | 0 |
| GE-CHK-158-A02 | Target X moment | -287.99189055 | kNm | 1e-08 | 0 |
| GE-CHK-158-A03 | Target Y moment | 17.602936749999998 | kNm | 1e-08 | 0 |
| GE-CHK-158-A04 | Inverse X-moment residual | 0 | kNm | 1e-08 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-08 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Omitting r cross F causes target errors deltaMx = +324.345142 kNm and deltaMy = -162.172571 kNm. Combining axial force from a different combination with this row of moments destroys the source identity of the vector.

**Report mapping:** The single EX6 SB301/G-prime vector passes through the unit/axis adapter, the explicit interface coordinate and r cross F to moment residuals in SuperstructureFoundationTransferResult. Retain separate superstructure and foundation model/generation fields.

**Qualification:** This is a complete coordinate and equilibrium benchmark using the source force vector. R and r are explicitly chosen; it does not claim an executed transfer between two actual ETABS models.

**Frozen input SHA-256:** `0c6ce09bdaeea4e44bcb80f1cccb45258555e2fc82e84c9afd6282ccd94ec4bf`

**Case SHA-256:** `087925ce6c05c343222a57c664c34437effa059cae498c382eafeb3f72780653`

### GE-ADP-01 — Create two combinations from an empty catalogue

**Check:** ADP-01 · **Kind:** CONTRACT_FIXTURE · **Population:** ADAPTER_CONTRACT_EXAMPLE

Concrete getter/setter acceptance scenario represented as frozen data; runtime execution remains separate.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

Declared contract fixture without an external source document. Its content is bound by the case hash and retained bank source hash.

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| initial_state | Empty combination catalogue; load cases G, Q, EX and EY exist; targets are DX and DY. | state | Declared adapter scenario |
| desired_definitions | DX=1.1016302G+Q+EX+0.3EY; DY=1.1016302G+Q+0.3EX+EY | LinearAdd | SRC-005 approximate vertical-earthquake benchmark; all leaves are load cases |

**Frozen contract data:**

```json
{
  "before_catalog": {},
  "desired_catalog": {
    "DX": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 1.0,
        "EY": 0.3
      }
    },
    "DY": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 0.3,
        "EY": 1.0
      }
    }
  },
  "expected_created": [
    "DX",
    "DY"
  ]
}
```

#### Calculation and intermediate results

GE-ADP-01-S01: **Operation and resulting state.**

Formula (display only): `Create two user-defined combinations, then read back all four terms of each with the getter.`

Substitution: `2*4`

Result: 8 terms (units: term)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| term_count | 8 | term | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-ADP-01-A01 | Created combination names | ["DX", "DY"] | identifier_list | 0 | 0 |
| GE-ADP-01-A02 | Four terms in each combination | 8 | term | 1e-09 | 0 |

**Tolerance rationale:** Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance. Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-ADP-01-A01, GE-ADP-01-A02 |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Change the desired or readback state and identify the affected field; this narrative variant is not an executed native transaction.

**Report mapping:** Prior getter state, mutation plan, native readback, expected final state and transaction journal.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `347dc8296d948fa530070940bd9236331af4c8a762d9fceea207f04bae5dc422`

**Case SHA-256:** `a833a7a422faa99a5b814fb9f505a3e509a5d0ac621ad89adb9719e3b28ba282`

### GE-ADP-02 — Complete a partial combination catalogue

**Check:** ADP-02 · **Kind:** CONTRACT_FIXTURE · **Population:** ADAPTER_CONTRACT_EXAMPLE

Concrete getter/setter acceptance scenario represented as frozen data; runtime execution remains separate.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

Declared contract fixture without an external source document. Its content is bound by the case hash and retained bank source hash.

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| initial_state | DX is correctly defined and assigned; DY is absent. | state | Declared adapter scenario |

**Frozen contract data:**

```json
{
  "before_catalog": {
    "DX": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 1.0,
        "EY": 0.3
      }
    }
  },
  "desired_catalog": {
    "DX": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 1.0,
        "EY": 0.3
      }
    },
    "DY": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 0.3,
        "EY": 1.0
      }
    }
  },
  "expected_created": [
    "DY"
  ]
}
```

#### Calculation and intermediate results

GE-ADP-02-S01: **Operation and resulting state.**

Formula (display only): `Create and assign only DY; retain the definition and revision of DX.`

Substitution: `2-1`

Result: 1 combination (units: combination)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| new_combination_count | 1 | combination | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-ADP-02-A01 | Missing combination count | 1 | combination | 1e-09 | 0 |
| GE-ADP-02-A02 | Preserved DX definition | true | bool | 0 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances. Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-ADP-02-A02 |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | SPECIFIED_EXECUTABLE | GE-ADP-02-A01 |

**Narrative variant:** Change the desired or readback state and identify the affected field; this narrative variant is not an executed native transaction.

**Report mapping:** Prior getter state, mutation plan, native readback, expected final state and transaction journal.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `12c45472ea174421d35fde74060b855a145350df7fc58eec350d4237bfa012da`

**Case SHA-256:** `acaa63f508a7742bee79426b8e30cd5a8b48d15f820fd3c03b1afa708f6738af`

### GE-ADP-03 — Same combination name with different contents

**Check:** ADP-03 · **Kind:** CONTRACT_FIXTURE · **Population:** ADAPTER_CONTRACT_EXAMPLE

Concrete getter/setter acceptance scenario represented as frozen data; runtime execution remains separate.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

Declared contract fixture without an external source document. Its content is bound by the case hash and retained bank source hash.

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| initial_state | EY has factor 0.4 in DX; the requested factor is 0.3. | state | Declared adapter scenario |

#### Calculation and intermediate results

GE-ADP-03-S01: **Operation and resulting state.**

Formula (display only): `Record the difference; create DX.V2 and bind the selection to it while preserving the previous definition.`

Substitution: `0.4-0.3`

Result: 0.1 coefficient (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| coefficient_difference | 0.1 | coefficient | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-ADP-03-A01 | Coefficient difference | 0.1 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Change the desired or readback state and identify the affected field; this narrative variant is not an executed native transaction.

**Report mapping:** Prior getter state, mutation plan, native readback, expected final state and transaction journal.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `9cb18f9eacba353006605d2978aaaf67509a7e466e23f9418508604157d7a726`

**Case SHA-256:** `a4af1cd7abf22ff0ae86b2fe8151083397544e65b797bd035e22a2c34251eb55`

### GE-ADP-04 — An extra term after a setter

**Check:** ADP-04 · **Kind:** CONTRACT_FIXTURE · **Population:** ADAPTER_CONTRACT_EXAMPLE

Concrete getter/setter acceptance scenario represented as frozen data; runtime execution remains separate.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

Declared contract fixture without an external source document. Its content is bound by the case hash and retained bank source hash.

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| initial_state | Desired children are G and EX; readback returns G, Q and EX; native return code is zero. | state | Declared adapter scenario |

**Frozen contract data:**

```json
{
  "desired_children": [
    "G",
    "EX"
  ],
  "readback_children": [
    "G",
    "Q",
    "EX"
  ],
  "native_return_code": 0
}
```

#### Calculation and intermediate results

GE-ADP-04-S01: **Operation and resulting state.**

Formula (display only): `Compare the complete child set. Do not report a successful definition when readback contains an extra Q term.`

Substitution: `sorted(['G','Q','EX']) == sorted(['G','EX'])`

Result: False (units: bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| definition_matches | false | bool | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-ADP-04-A01 | Extra child prevents equality | false | bool | 0 | 0 |
| GE-ADP-04-A02 | Extra-term count | 1 | term | 1e-09 | 0 |

**Tolerance rationale:** Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance. Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-ADP-04-A01, GE-ADP-04-A02 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Change the desired or readback state and identify the affected field; this narrative variant is not an executed native transaction.

**Report mapping:** Prior getter state, mutation plan, native readback, expected final state and transaction journal.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `ef6e1855d66ce69891a0efc1fe8723490dc496a94569bd89b88f5637c89fb206`

**Case SHA-256:** `b2c43b1b870cefa6a59cb804497a1ac4d729269ddc9e6ac918cae4645a48c2b5`

### GE-ADP-05 — Apply the same desired catalogue a second time

**Check:** ADP-05 · **Kind:** CONTRACT_FIXTURE · **Population:** ADAPTER_CONTRACT_EXAMPLE

Concrete getter/setter acceptance scenario represented as frozen data; runtime execution remains separate.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

Declared contract fixture without an external source document. Its content is bound by the case hash and retained bank source hash.

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| initial_state | The current catalogue exactly matches the desired definitions. | state | Declared adapter scenario |

**Frozen contract data:**

```json
{
  "desired_catalog": {
    "DX": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 1.0,
        "EY": 0.3
      }
    },
    "DY": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 0.3,
        "EY": 1.0
      }
    }
  },
  "readback_catalog": {
    "DY": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 0.3,
        "EY": 1.0
      }
    },
    "DX": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 1.0,
        "EY": 0.3
      }
    }
  },
  "expected_mutations": []
}
```

#### Calculation and intermediate results

GE-ADP-05-S01: **Operation and resulting state.**

Formula (display only): `Create, delete and modify lists must all be empty.`

Substitution: `0+0+0`

Result: 0 mutations (units: mutation)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| expected_write_count | 0 | operation | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-ADP-05-A01 | Normalized content equality despite order | true | bool | 0 | 0 |
| GE-ADP-05-A02 | Second-application mutation count | 0 | mutation | 1e-09 | 0 |

**Tolerance rationale:** Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance. Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-ADP-05-A01, GE-ADP-05-A02 |
| negative | OPEN | None |
| boundary | SPECIFIED_EXECUTABLE | GE-ADP-05-A02 |
| missing_source | OPEN | None |

**Narrative variant:** Change the desired or readback state and identify the affected field; this narrative variant is not an executed native transaction.

**Report mapping:** Prior getter state, mutation plan, native readback, expected final state and transaction journal.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `eceeaa3ec382e1c5b9fde39663fa50acc42faedad24411ccd4d9547e450b69d7`

**Case SHA-256:** `9d2cc55ed1d6bd9c43cae20576c99cbeba3c249ef037c531c4e4abc01101d990`

### GE-ADP-06 — Restore units and result selections

**Check:** ADP-06 · **Kind:** CONTRACT_FIXTURE · **Population:** ADAPTER_CONTRACT_EXAMPLE

Concrete getter/setter acceptance scenario represented as frozen data; runtime execution remains separate.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

Declared contract fixture without an external source document. Its content is bound by the case hash and retained bank source hash.

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| initial_state | Initial units are kN and m with LC_DL selected; capture temporarily uses N and mm. | state | Declared adapter scenario |
| initial_selections | {"units": {"force": "kN", "length": "m", "temperature": "C"}, "selected_cases": ["LC_DL"], "selected_combinations": ["DX"]} | session record | Declared session fixture including the temperature unit |

**Frozen contract data:**

```json
{
  "before": {
    "units": {
      "force": "kN",
      "length": "m",
      "temperature": "C"
    },
    "selected_cases": [
      "LC_DL"
    ],
    "selected_combinations": [
      "DX"
    ]
  },
  "after_success": {
    "units": {
      "force": "kN",
      "length": "m",
      "temperature": "C"
    },
    "selected_cases": [
      "LC_DL"
    ],
    "selected_combinations": [
      "DX"
    ]
  },
  "after_error": {
    "units": {
      "force": "kN",
      "length": "m",
      "temperature": "C"
    },
    "selected_cases": [
      "LC_DL"
    ],
    "selected_combinations": [
      "DX"
    ]
  },
  "after_cancel": {
    "units": {
      "force": "kN",
      "length": "m",
      "temperature": "C"
    },
    "selected_cases": [
      "LC_DL"
    ],
    "selected_combinations": [
      "DX"
    ]
  },
  "bad_after_error": {
    "units": {
      "force": "kN",
      "length": "mm",
      "temperature": "C"
    },
    "selected_cases": [
      "LC_DL"
    ],
    "selected_combinations": [
      "DX"
    ]
  }
}
```

#### Calculation and intermediate results

GE-ADP-06-S01: **Operation and resulting state.**

Formula (display only): `Restore the initial units and result selections after success, error and cancellation.`

Substitution: `10*1000`

Result: 10000 N (units: N)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| session_after_success | {"units": {"force": "kN", "length": "m", "temperature": "C"}, "selected_cases": ["LC_DL"], "selected_combinations": ["DX"]} | record | Expected contract state |
| session_after_error | {"units": {"force": "kN", "length": "m", "temperature": "C"}, "selected_cases": ["LC_DL"], "selected_combinations": ["DX"]} | record | Expected contract state |
| session_after_cancellation | {"units": {"force": "kN", "length": "m", "temperature": "C"}, "selected_cases": ["LC_DL"], "selected_combinations": ["DX"]} | record | Expected contract state |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-ADP-06-A01 | Complete state after success | true | bool | 0 | 0 |
| GE-ADP-06-A02 | Complete state after error | true | bool | 0 | 0 |
| GE-ADP-06-A03 | Complete state after cancellation | true | bool | 0 | 0 |
| GE-ADP-06-A04 | Wrong restored length unit is detected | false | bool | 0 | 0 |

**Tolerance rationale:** Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-ADP-06-A01, GE-ADP-06-A02, GE-ADP-06-A03 |
| negative | SPECIFIED_EXECUTABLE | GE-ADP-06-A04 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Change the desired or readback state and identify the affected field; this narrative variant is not an executed native transaction.

**Report mapping:** Prior getter state, mutation plan, native readback, expected final state and transaction journal.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `f734df01cf3aabecb916949b1426a19993a06d5ca0ebc31e134db8a56c0b380b`

**Case SHA-256:** `2c0c39dd0698a57cfe4f91baa0ea669f41276ee3c24e3e73d810e3e7ee3d5092`

### GE-ADP-07 — Direction and analysis-element-side coverage

**Check:** ADP-07 · **Kind:** CONTRACT_FIXTURE · **Population:** ADAPTER_CONTRACT_EXAMPLE

Concrete getter/setter acceptance scenario represented as frozen data; runtime execution remains separate.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

Declared contract fixture without an external source document. Its content is bound by the case hash and retained bank source hash.

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| initial_state | DX has four rows and DY has three; each requires four. | state | Declared adapter scenario |

#### Calculation and intermediate results

GE-ADP-07-S01: **Operation and resulting state.**

Formula (display only): `Report the missing DY/E2/I row with its identity.`

Substitution: `(4+3)/(2*4)`

Result: Coverage ratio 0.875 (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| coverage_ratio | 0.875 | ratio | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-ADP-07-A01 | Scope coverage ratio | 0.875 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | SPECIFIED_EXECUTABLE | GE-ADP-07-A01 |

**Narrative variant:** Change the desired or readback state and identify the affected field; this narrative variant is not an executed native transaction.

**Report mapping:** Prior getter state, mutation plan, native readback, expected final state and transaction journal.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `5c418826ab9587b79698a74ec2b7c429582f973da2f68cb78309766975f41a96`

**Case SHA-256:** `accfdd365772f71d12c5e6cfb4e3e6dd56dcf2a0cd2c6613907bde219d7eccf3`

### GE-ADP-08 — Analysis generation after a P-Delta change

**Check:** ADP-08 · **Kind:** CONTRACT_FIXTURE · **Population:** ADAPTER_CONTRACT_EXAMPLE

Concrete getter/setter acceptance scenario represented as frozen data; runtime execution remains separate.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

Declared contract fixture without an external source document. Its content is bound by the case hash and retained bank source hash.

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| initial_state | Target analysis generation is 8; existing forces belong to generation 7. | state | Declared adapter scenario |

**Frozen contract data:**

```json
{
  "target_generation": 8,
  "old_force_generation": 7
}
```

#### Calculation and intermediate results

GE-ADP-08-S01: **Operation and resulting state.**

Formula (display only): `Capture forces and convergence evidence from the new analysis generation.`

Substitution: `7 == 8`

Result: False (units: bool)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| generation_matches | false | bool | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-ADP-08-A01 | Old forces do not belong to the new generation | false | bool | 0 | 0 |

**Tolerance rationale:** Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | SPECIFIED_EXECUTABLE | GE-ADP-08-A01 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | SPECIFIED_EXECUTABLE | GE-ADP-08-A01 |

**Narrative variant:** Change the desired or readback state and identify the affected field; this narrative variant is not an executed native transaction.

**Report mapping:** Prior getter state, mutation plan, native readback, expected final state and transaction journal.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `68ad26cc7defc717fa39ce31f88886c64e7c2e97f9979e3baa55a1455a02a5bc`

**Case SHA-256:** `6562ff62648b6992ab24229aefc518a285b0b2d6b94864bf1a03473cf8e9ab2a`

### GE-ADP-09 — Reinforcement revision propagates to dependent results

**Check:** ADP-09 · **Kind:** CONTRACT_FIXTURE · **Population:** ADAPTER_CONTRACT_EXAMPLE

Concrete getter/setter acceptance scenario represented as frozen data; runtime execution remains separate.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

Declared contract fixture without an external source document. Its content is bound by the case hash and retained bank source hash.

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| initial_state | Replace four Phi18 bars with eight Phi18 bars; actual bar coordinates are recorded separately. | state | Declared adapter scenario |

#### Calculation and intermediate results

GE-ADP-09-S01: **Operation and resulting state.**

Formula (display only): `As, Is, EI, Nk, PMM, member-end capacities and joint consumers must use the new reinforcement revision.`

Substitution: `8 × π × 18² / 4`

Result: 2035.752039526186 mm² (units: mm²)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| revised_As | 2035.752039526186 | mm² | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-ADP-09-A01 | Revised reinforcement area | 2035.752039526186 | mm² | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Change the desired or readback state and identify the affected field; this narrative variant is not an executed native transaction.

**Report mapping:** Prior getter state, mutation plan, native readback, expected final state and transaction journal.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `ce169e875fb84cdc83d491cbb0e33c06eb2d3dda3e7cc5ab6ba96191fe40e4f7`

**Case SHA-256:** `e9a5fadf52f31a8b941460b925bba8dc12db2e20d5f1016dcb67b9fb013c6b2a`

### GE-ADP-10 — Change one member using a shared section

**Check:** ADP-10 · **Kind:** CONTRACT_FIXTURE · **Population:** ADAPTER_CONTRACT_EXAMPLE

Concrete getter/setter acceptance scenario represented as frozen data; runtime execution remains separate.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

Declared contract fixture without an external source document. Its content is bound by the case hash and retained bank source hash.

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| initial_state | Ten columns share one section; only one is targeted for change. | state | Declared adapter scenario |

#### Calculation and intermediate results

GE-ADP-10-S01: **Operation and resulting state.**

Formula (display only): `Clone the section and assign it only to the target; retain the other nine assignments.`

Substitution: `10-1`

Result: 9 members (units: member)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| members_retaining_original_section | 9 | member | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-ADP-10-A01 | Members retaining the original section | 9 | member | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Change the desired or readback state and identify the affected field; this narrative variant is not an executed native transaction.

**Report mapping:** Prior getter state, mutation plan, native readback, expected final state and transaction journal.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `bd5f991956c806e6da0e613dac492e0958652a5a0f9c81202972edb6e24962ca`

**Case SHA-256:** `a6bc0ad68b3a8db23bd75f9ebb2aaa6db5e64bb61585fb9af25913b491a1a1d8`

### GE-ADP-11 — An interrupted mutation sequence

**Check:** ADP-11 · **Kind:** CONTRACT_FIXTURE · **Population:** ADAPTER_CONTRACT_EXAMPLE

Concrete getter/setter acceptance scenario represented as frozen data; runtime execution remains separate.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

Declared contract fixture without an external source document. Its content is bound by the case hash and retained bank source hash.

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| initial_state | Two of three writes have been verified; the third failed. | state | Declared adapter scenario |

#### Calculation and intermediate results

GE-ADP-11-S01: **Operation and resulting state.**

Formula (display only): `The journal records the final state; rollback and analysis validity require separate verification.`

Substitution: `3-2`

Result: 1 operation (units: operation)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| incomplete_operation_count | 1 | operation | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-ADP-11-A01 | Incomplete operation count | 1 | operation | 1e-09 | 0 |

**Tolerance rationale:** Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | OPEN | None |
| negative | OPEN | None |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** Change the desired or readback state and identify the affected field; this narrative variant is not an executed native transaction.

**Report mapping:** Prior getter state, mutation plan, native readback, expected final state and transaction journal.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `9281b21027277636407195909f3df0b0703098ae84013b5f3370630ffef944c1`

**Case SHA-256:** `a4669ef512cb241aa7d7a4cf7a21e3abc66981a0c2497a8577d99e8339d1cf28`

### GE-ADP-12 — Save and reopen the model

**Check:** ADP-12 · **Kind:** CONTRACT_FIXTURE · **Population:** ADAPTER_CONTRACT_EXAMPLE

Concrete getter/setter acceptance scenario represented as frozen data; runtime execution remains separate.

**Normative or contract basis:** Source and adapter contract; recipe sections 2 to 4 and 17

#### Source trace

Declared contract fixture without an external source document. Its content is bound by the case hash and retained bank source hash.

#### Inputs

| Name | Value | Unit | Origin |
| --- | --- | --- | --- |
| initial_state | The saved coefficient is 0.3 and the reopened coefficient is 0.3. | state | Declared adapter scenario |

**Frozen contract data:**

```json
{
  "saved_catalog": {
    "DX": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 1.0,
        "EY": 0.3
      }
    },
    "DY": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 0.3,
        "EY": 1.0
      }
    }
  },
  "readback_catalog": {
    "DX": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 1.0,
        "EY": 0.3
      }
    },
    "DY": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 0.3,
        "EY": 1.0
      }
    }
  },
  "wrong_readback": {
    "DX": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 1.0,
        "EY": 0.4
      }
    },
    "DY": {
      "operator": "LinearAdd",
      "case_terms": {
        "G": 1.1016302,
        "Q": 1.0,
        "EX": 0.3,
        "EY": 1.0
      }
    }
  }
}
```

#### Calculation and intermediate results

GE-ADP-12-S01: **Operation and resulting state.**

Formula (display only): `Recompare complete definitions and assignments; a readback coefficient of 0.4 is not equivalent.`

Substitution: `abs(0.3-0.3)`

Result: 0 coefficient difference (units: 1)

#### Expected results

| Quantity | Expected value | Unit | Basis |
| --- | --- | --- | --- |
| readback_difference | 0 | coefficient | Expected result of the declared example |

#### Independent assertion targets

| Assertion | Description | Expected | Unit | Absolute tolerance | Relative tolerance |
| --- | --- | --- | --- | --- | --- |
| GE-ADP-12-A01 | Complete reopened definition | true | bool | 0 | 0 |
| GE-ADP-12-A02 | Incorrect readback is detected | false | bool | 0 | 0 |
| GE-ADP-12-A03 | Incorrect coefficient difference | 0.1 | 1 | 1e-09 | 0 |

**Tolerance rationale:** Exact identity or truth value; no numerical or engineering acceptance tolerance applies. The inherited numerical comparator settings are retained separately for provenance. Inherited absolute allowance 1e-09 and relative allowance 0 apply only to reproducing this frozen numerical benchmark, including decimal and binary floating-point rounding. They are not engineering acceptance tolerances.

#### Scenario coverage

| Category | Status | Assertion references |
| --- | --- | --- |
| positive | SPECIFIED_EXECUTABLE | GE-ADP-12-A01 |
| negative | SPECIFIED_EXECUTABLE | GE-ADP-12-A02, GE-ADP-12-A03 |
| boundary | SPECIFIED_NOT_EXECUTED | None |
| missing_source | OPEN | None |

**Narrative variant:** If reopened DX contains EY = 0.4, the difference is 0.1 and complete-definition equality is false. Retaining a catalogue count of two is insufficient.

**Report mapping:** Prior getter state, mutation plan, native readback, expected final state and transaction journal.

**Qualification:** This is a concrete data and transaction fixture. It does not execute a live ETABS getter/setter or the YENI production runtime.

**Frozen input SHA-256:** `a1d886ab7ee5700880a552392837bf4c2e38f2a04d799a607b4cde037720b1f0`

**Case SHA-256:** `977a92ad42e4684f50e4c5ca66ddfd1e3ee50e1de4cc4d17114d0ad307d2829f`



## Appendix D — Independent modal-to-alpha chain


### Purpose and acceptance boundary

`GE-CHAIN-MODAL-ALPHA-001` is an additional `DERIVED_BENCHMARK`. It follows the required sequence: modal numerical precision, applied accidental eccentricity, modal and directional combination, SCWB axial demand, storey shear allocation, and alpha feedback. All numerical inputs, intermediate quantities, expected values and identities are available in `PRIORITY_CHAIN.json`. `tools/verify_priority_chain.py` repeats the declared arithmetic without importing YENI.

This is a complete arithmetic and provenance example for that sequence. Its signed modal fields and capacity curves are declared reference inputs. It does not solve a finite-element eigenproblem, prove a physical reinforcement cage, or replace the existing section-capacity owner. Actual building evidence still has to supply those inputs. The production comparison, recorded-source pipeline replay, live ETABS validation and engineering acceptance levels remain `NOT_RUN`.

The example is one additional fixture. Its source rows, combination definitions and assertion records are separate populations. None increases the 73 CHECK count or replaces the 44 existing production-comparison records, the original 333 recipe expressions, or the separate 333 PDF-bank comparisons.

The published source inspected for integration context is commit `b255c3030c09c88a17bbec766fc2bb22682ad027` on `baseline/local_import`. The user's local commit `a2e26b664d9b2b217e828de2c1df0c3df26068b1` and subsequent work remain `NOT_INSPECTED`. The published checkpoint identifies GAP-018, GAP-013 and GAP-016 as the relevant sequence; this example does not assert their present local status.

### Common source identity and physical scope

Every source row and every intermediate result belongs to the common identity record in the JSON. The record contains `source_id`, the canonical input SHA-256, `model_id`, `analysis_generation_id`, `modal_source_id`, `method_revision`, `storey_id`, `story_cut_id`, and the initial/revised column and beam capacity-input revisions. Case, mode, element side and physical-cut identifiers refine that common identity. These identifiers cannot be replaced by matching filenames or storey labels.

The evaluation scope is the middle storey S2 of a declared three-storey frame. Four column lines continue through both joints bounding S2. This avoids using the single-storey or roof-discontinuation exception of TBDY 7.3.5.3(b). The physical storey height is 3 m, end offsets are zero and end releases are absent. The diaphragm is 10 m by 10 m. Column-line coordinates are C1=(-3,-3), C2=(3,-3), C3=(3,3), and C4=(-3,3), in metres.

For each column line, the four recorded end cuts are S1/J, S2/I, S2/J and S3/I. They support the lower and upper joint checks and the common S2 bottom-cut shear census. Four spectrum cases, `X_E_MINUS`, `X_E_PLUS`, `Y_E_MINUS` and `Y_E_PLUS`, each contain two declared signed modal terms at every cut. The independent denominator is therefore 16 cuts × 4 cases × 2 terms = 128 rows. A duplicate row cannot replace an omitted cut/mode/case tuple.

The fixture uses N>0 for compression. Global XYZ is right-handed with Z upward; local 1=Z, local 2=X and local 3=Y. X excitation bends about global Y/local 3; Y excitation bends about global X/local 2. Storey shear components are resolved on one common physical cut orientation. Each source row records both object and element station and the element side. The actual adapter must establish its CSI-to-domain sign conversion before these quantities can be compared.

### Step 1 Modal numerical precision

The two supplied periods are 1.0 s and 0.5 s. Both active modal damping ratios are explicitly 0.05. Equal active damping is an input to this branch; a case-level default of 5% does not by itself establish the damping used by every native mode.

For equal damping, TBDY 2018 Eq. 4B.5b gives, with beta=T2/T1=0.5,

`rho12 = 8 xi² (1+beta) beta^(3/2) / [(1-beta²)² + 4 xi² beta (1+beta)²]`

The result is `rho12 = 0.01848645179572673266407436240797`. The two-by-two correlation matrix has unit diagonal and this off-diagonal value. Its eigenvalues are 1+rho and 1-rho, both positive. For two signed modal amplitudes a and b, Eq. 4B.4 becomes:

`R² = a² + b² + 2 rho a b = (1-rho)(a²+b²) + rho(a+b)²`.

The second form is used by the independent Decimal(80) verifier. It avoids subtracting almost equal large squares in the near-cancellation stress case. The input periods, damping, amplitude units, normalization and rounding precision are retained before any modal or directional envelope is formed.

The main fixture's X storey amplitudes are 100 and 50 kN; its Y amplitudes are 80 and 40 kN. Thus `R_X = 112.6271038336566 kN` and `R_Y = 90.1016830669253 kN`.

A separate numerical stress variant uses periods 1 and 0.9999999995 s, damping 0.05, and amplitudes +1,000,000 and -999,999.9999 kN. Decimal(80) gives rho=0.99999999999999997496875 and a response of 0.007076192480425119 kN. Converting this correlation to binary64 rounds it to one; the illustrated binary64 response is about 0.000099999947 kN. The verifier detects this loss of correlation precision. This is a mathematical stress witness, not a reported defect in ETABS or YENI. Actual tolerances must account for native export precision and active solver settings.

### Step 2 Applied accidental eccentricity effects

The eccentricity magnitude is 0.05 × 10 = 0.5 m. The fixture supplies actual signed torsional force increments in addition to the centred-case field. It does not infer an applied effect from a checked setting.

For X excitation, a positive shift along global Y produces `Mz = -e Vx`; for Y excitation, a positive shift along global X produces `Mz = +e Vy`. With the supplied corner coordinates, `sum(x²+y²)=72 m²`. The declared linear reference response operator is:

`delta Fx_i = -Mz y_i / 72`, and `delta Fy_i = +Mz x_i / 72`.

For X_E_PLUS, mode 1, the imposed increment is Mz=-50 kN m. The increments in Fx are (-2.083333, -2.083333, +2.083333, +2.083333) kN; the Fy increments are (+2.083333, -2.083333, -2.083333, +2.083333) kN. Their total horizontal force is zero, while `sum(x delta Fy - y delta Fx) = -50 kN m`. Mode 2 has half these increments. The other direction/eccentricity branches are recorded independently. Their total force and applied torque are checked in the same way.

The centred X fractions are (0.4,0.3,0.2,0.1), so the first X_E_PLUS modal Fx field is (37.916667,27.916667,22.083333,12.083333) kN. This is combined with its own second modal field, rather than with the maximum member values from another branch.

This reference operator makes the applied-effect arithmetic transparent. It does not prove that adding eV torsion to an unshifted modal result reproduces every ETABS or TBDY modelling route. TBDY 4.5.10 includes shifted loading and a modal mass-inertia alternative; CSI's response-spectrum help also distinguishes diaphragm width, eccentricity overwrites and applied torsional moments. The actual engine must capture the implemented branch, native torsional contributions and combination order, or qualify an independently justified reconstruction. A setting value of 0.05, an unverified diaphragm width, or a nonzero output moment alone is insufficient evidence.

### Step 3 Modal and directional combination

Each fixture spectrum case has one active horizontal excitation direction. Therefore its internal directional SRSS is the identity: SRSS(R,0)=R. CQC is first applied to signed modal contributions of each scalar response and each fixed eccentricity case. The X and Y case results then enter the separate TBDY 4.4.2.1 design families:

`± E_X ± 0.3 E_Y`, and `± 0.3 E_X ± E_Y`.

These are different combination levels. Applying native two-direction SRSS and then treating that already combined result as an independent X or Y primitive would double-combine effects. The captured native load directions, angles, scales and directional rule determine whether a source can be used as an X/Y primitive.

The fixture catalogue explicitly contains four eccentricity pairs, four sign pairs, two primary-direction families and two gravity families: 4 × 4 × 2 × 2 = 64 scalar combination definitions. The selected `ductile` design group contains all 64 IDs; the expected ledger is derived from that catalogue before responses are evaluated. Case names alone do not define group membership or prove the coefficients.

For axial demand, with S=H=0, SDS=0.5 and the approximate vertical-earthquake branch of TBDY 4.4.3.2, the two gravity portions are:

`G + Q + 0.3 E_Z = 1.1 G + Q`, and `0.9 G - 0.3 E_Z = 0.8 G`.

The special vertical-analysis elements of 4.4.3.1 are outside this declared fixture. Actual applicability must be established from the physical model.

CQC responses and directional combinations remain scalar magnitudes or scalar intervals. The record does not assemble an N-M2-M3-V vector by combining independently attained extrema. In this example, the combined axial amplitudes are `A_X + 0.3 A_Y` and `0.3 A_X + A_Y`; their interval hull can safely bound the declared scalar axial families. This does not establish concurrent bending or shear at either axial endpoint.

### Step 4 Governing SCWB axial demand

TBDY 7.3.5.2 requires the direction-compatible axial forces that minimize the column resistance moments. Maximum compression is not a general substitute for this search. This fixture demonstrates that distinction using explicit analytic capacity-input curves:

`C_pair(N) = C0 - 0.0002 (N-700)²`, in kN m, with N in kN.

`C_pair` is the sum of the two column-end resistances at a joint. Each column-end input is one half of the curve. The curves apply to both bounding joints and to both senses of X and Y for this symmetric reference capacity input. They are not derived RC section capacities. Their initial C0 values are (280,275,270,210) kN m.

The lower and upper axial bounds use the complete two-gravity, two-direction family. Because this curve is concave, its minimum on a closed interval is attained at an endpoint. Both endpoints are evaluated. Here the lower-compression endpoint governs every line.

| Column line | N lower kN | N upper kN | Governing N kN | Initial column-pair resistance kN m | Beam threshold kN m |
|---|---:|---:|---:|---:|---:|
| C1 | 328.431380 | 721.568620 | 328.431380 | 252.387352 | 240 |
| C2 | 424.095472 | 815.904528 | 424.095472 | 259.775338 | 240 |
| C3 | 414.805284 | 730.194716 | 414.805284 | 253.732795 | 240 |
| C4 | 345.358477 | 609.641523 | 345.358477 | 184.845878 | 240 |

Both beam-face capacity inputs are 100 kN m, giving `1.2 (100+100)=240 kN m`. C1, C2 and C3 meet the SCWB inequality at both joints; C4 does not. The ledger contains all 4 lines × 2 joints × 2 directions × 2 signs = 32 classifications. With Ac=90,000 mm² and fck=25 MPa, the low-axial exemption threshold is 225 kN. Every lower bound exceeds that threshold, so no low-axial exemption is credited.

For an actual model, the existing section-capacity owner must use bound physical/selected reinforcement and return the minimum resistance over the applicable axial family. A finite set of axial samples needs an interpolation/error or extremum certificate before it proves the minimum on a continuous interval. Minimizing each column resistance separately gives a conservative joint lower bound when the actual joint axial states are correlated; that lower bound must be labelled as a bound, not as one physical simultaneous state. A failing conservative lower bound requires refinement before it is called a physical failure.

### Step 5 Storey shear allocation

The denominator contains every S2 frame column on the same bottom cut. There are no walls in this reference scope. The numerator contains C1, C2 and C3, which meet SCWB at both joints. For each excitation/eccentricity branch, signed member shears are summed within each mode first; CQC is then applied to the eligible and total modal sums.

| Case | Total modal shears kN | Eligible modal shears kN | Vik kN | Vis kN | alpha |
|---|---|---|---:|---:|---:|
| X_E_MINUS | (100,50) | (92.083333,46.041667) | 112.627104 | 103.710791 | 0.9208333333 |
| X_E_PLUS | (100,50) | (87.916667,43.958333) | 112.627104 | 99.017995 | 0.8791666667 |
| Y_E_MINUS | (80,40) | (70.333333,35.166667) | 90.101683 | 79.214396 | 0.8791666667 |
| Y_E_PLUS | (80,40) | (73.666667,36.833333) | 90.101683 | 82.968633 | 0.9208333333 |

The governing value is exactly alpha=211/240=0.8791666667; its reciprocal is 240/211=1.1374407583. It lies in the conditional interval [0.70,1.00] of TBDY 7.3.6.

The main fixture has a deliberate proof property: within each branch, every member has the same allocation fraction in both modal terms. The eligible fraction is therefore constant for any common modal time history, including sign reversals. This proportionality proves that the subset fraction and the ratio of CQC totals are the same in this fixture. Taking the governing minimum over the independently evaluated eccentricity branches preserves the declared denominator.

That proof does not extend automatically to actual non-proportional modal fields. A counterexample with member modal vectors (40,-10), (30,20), (20,25) and (10,15) kN gives 127.897127 kN when individual CQC peaks are added, but only 112.627104 kN when signed modal member forces are summed before combination. They are different response quantities. A stronger cancellation witness has an eligible modal force of +10 kN and an ineligible force of -9 kN in the same mode: the ratio of their independently combined subset and total is 10, not a physical fraction bounded by one. The engine must not clip this result to one or silently reinterpret the denominator. Actual non-proportional spectral allocation remains a method-acceptance requirement, with common modal or time-domain evidence.

The alpha census here is direction-specific X or Y earthquake shear. The separate 100/30 families are used for member design and governing axial demand. A production method that instead uses combined-direction story effects must define and independently validate that denominator explicitly.

### Step 6 Alpha feedback and fixed point

The scalar demand bounds are built from the immutable original modal source. The declared factored gravity moment bounds are (40,70,80,50) kN m. The seismic moment bound equals 1.5 times the governing horizontal shear bound for the declared 3 m double-curvature reference field. The conditional multiplier is applied to the total M and V design bounds of C1-C3 only. N, torsion and the original captured source stay unchanged. C4 is designed under its unamplified gravity-plus-earthquake demand, as the conditional branch requires.

| Column line | Original M bound kN m | Alpha multiplier | Revised M bound kN m | Initial single-column Mr bound kN m | Revised Mr bound kN m |
|---|---:|---:|---:|---:|---:|
| C1 | 111.940563 | 1.1374407583 | 127.325758 | 126.193676 | 136.193676 |
| C2 | 125.046497 | 1.1374407583 | 142.232982 | 129.887669 | 147.387669 |
| C3 | 118.152431 | 1.1374407583 | 134.391391 | 126.866397 | 141.866397 |
| C4 | 71.258366 | 1 | 71.258366 | 92.422939 | 92.422939 |

Before alpha feedback, all four moment bounds are within their initial single-column reference capacities. After feedback, C1-C3 require a revision. The revised C0 input vector is (300,310,300,210) kN m. It increases the three affected capacities while leaving C4 unchanged. The declared shear-resistance inputs (80,70,50,35) kN also exceed the revised shear bounds. This is an arithmetic candidate-revision demonstration; real bar counts, diameters, topology, anchorage and detailing must come from the existing design/capacity owners.

| Iteration | Capacity-input revision | Eligible set | Governing alpha | Result |
|---|---|---|---:|---|
| 0 | A01 | C1,C2,C3 | 211/240 | Original capacities require revision after feedback. |
| 1 | A02 | C1,C2,C3 | 211/240 | Recompute all bounds from the frozen original source; revised capacities cover them. |
| 2 | A02 | C1,C2,C3 | 211/240 | Repeated classification, factor, capacities and original-source demands are unchanged. |

The reference chain has a fixed point. Reapplying 240/211 to an already amplified demand would produce an incorrect additional increase and is explicitly detected. The existing production iteration must additionally run the dependent PMM, shear, confinement and joint owners with the new cage revision. A stable alpha alone is not convergence. A repeated candidate cycle, infeasible capacity, changed source generation, unresolved dependent check or maximum-iteration stop must retain its actual failure/unresolved status.

### Eight corner sufficiency and nonlinear transformations

Eight box corners can bound a demand set only under stated mathematical conditions. Every admissible concurrent vector must lie in the box, using the same source, case family, physical cut, axes and units. The resistance set must be certified convex for one fixed geometry, material and cage revision. If all vertices lie in that convex set, their convex hull also lies in it. This is a set-containment argument, not a reconstruction of concurrent forces.

An affine demand transformation preserves the vertex-convex-hull argument. An N-dependent moment magnifier generally is not affine. Its denominator must stay strictly away from zero on the entire axial interval; branch changes, monotonicity and interior extrema need proof or a certified enclosing image. A box spanning N/Ncr=1 cannot be qualified from its two axial endpoint calculations. Capacity interpolation, material-state changes and selection of different cages at different vertices likewise require their own evidence.

A mathematical counterexample is included: `u(N,M2,M3)=abs(M2)/(2+(N-0.5)²)` on N in [0,1], M2 in [-2.1,2.1] and M3 in [-0.1,0.1]. All eight corners have u=0.9333333, while N=0.5 and |M2|=2.1 gives u=1.05. The accepted set is nonconvex. This is not an RC model; it demonstrates why a generic nonlinear operation cannot inherit whole-box sufficiency from corner checks.

For the actual engine, corner results remain explicitly conditional until box containment, resistance convexity and the transformation proof are available. A conservative-box exceedance does not prove a realizable vector fails. Passing corners without the required set-containment proof does not close the engineering method.

### Actual source evidence still required

The published checkpoint and this fixture identify the following evidence to bind through the existing source gateway and pipeline:

1. The local target tree, dirty diff and untracked implementation/test manifest, each with file hashes. The published snapshot cannot substitute for those bytes.
2. Native modal amplitudes, amplitude normalization, period precision, actual modal damping/overrides, spectrum ordinates, case directions, angles and scale factors.
3. Actual applied accidental-torsion contributions, diaphragm membership/width, default and overwritten eccentricities, and the installed ETABS build's combination order.
4. The independent expected case/mode/cut denominator, including both sides of internal analysis-element cuts and all connected joint members.
5. Direction-compatible axial families and independently validated column/beam capacities using explicitly bound actual or selected reinforcement revisions.
6. An accepted storey-shear allocation for the actual non-proportional modal fields; the proportional proof in this fixture does not qualify that case.
7. The existing production owners' result comparisons, downstream rechecks, sealed pipeline replay, unchanged report projection and any live-source validation still required.

These are inputs and acceptance requirements for the existing owners, not requests for a second solver, parallel pipeline or ETABS attachment. The current published owners include `engineering/demand_sources.py`, `engineering/mixed_demands.py`, `column_engine/spectral_envelope.py`, `column_engine/story_alpha.py` and `engineering/alpha_iteration.py`; precise code-verified bindings and local-inspection status belong to `CHECK_MAPPING.json`.

### Reproduction and evidence

Run `python tools/verify_priority_chain.py --fixture PRIORITY_CHAIN.json --output PRIORITY_CHAIN_RESULTS.json` from the delivery root. The checker is Python-standard-library-only and uses 80-digit Decimal arithmetic. Formula prose in JSON and this document is never interpreted. The command reports the fixture hash, checker hash, runtime, precision, individual differences and limits.

The original authoring calculation used binary64 Cholesky-form CQC; the delivered independent replay uses Decimal covariance-eigenbasis arithmetic. The exact alpha fraction supplies an additional algebraic check. Both reference calculations are independent of the YENI production arithmetic. This establishes reproducible example arithmetic, not production-owner equivalence.

Normative locations: `GE-S09`, TBDY 2018, physical PDF pp.62-63 (directional/vertical/load combinations), 69-70 (accidental eccentricity), 87-88 (modal combination), and 137-139 (SCWB and alpha). The source SHA-256 is recorded in the JSON and source manifest. CSI's public response-spectrum help is identified separately for software-setting semantics; it does not replace the TBDY method's applicability assessment.


## Appendix E — Verification and integration record

### Six execution levels

| Level | Current result | Evidence and limit |
| --- | --- | --- |
| Document/schema consistency | VALID | 73 identities, 85 cases, source/atlas links, 142 source-file hashes and 88 distinct source symbols; six negative contract probes detected. This is not a full semantic audit. |
| Independent example arithmetic | MATCH | 333/333 preserved recipe assertions and, separately, 1,294/1,294 assertions in the additional chain fixture. |
| Actual existing-owner comparison | MATCH, limited scope | Three primitive values from two actual functions at the pinned published commit; zero complete engineering controls closed. |
| Recorded-source pipeline replay | NOT_RUN | No new frozen-project execution of EnginePipelineRunner in this delivery. |
| Live ETABS source validation | NOT_RUN | No connection, native mutation, reanalysis or live getter/setter transaction. |
| Engineering acceptance | NOT_RUN | This documentation does not approve a method, building or release. |

The current owner outputs are 1080 kN for the TBDY axial limit, 1620 kN for the TS 500 axial limit, and 24 mm for minimum eccentricity at a 300 mm bending depth. They are linked to GE-CHK-004-A01, GE-CHK-005-A02 and GE-CHK-115-A01. The owner file is `src/tbdy_next/column_engine/ts500_column.py`; the existing functions are `section_axial_limits_kn` and `minimum_eccentricity_mm`. The comparator checks five imported dependency files before execution. Its actual parameter/output mapping and numerical differences are in `evidence/OWNER_COMPARISONS.json`.

Every current record contains its command, interpreter/environment, file/tool hashes, result and limits. `VERIFICATION_RESULTS.json` indexes the records and separates current execution from historical observations. Its local a2e-plus-dirty execution remains NOT_RUN, and that local source remains NOT_INSPECTED.

### Scenario coverage is explicit

The counts below concern all 85 examples, including 12 adapter fixtures. “Executable” identifies a frozen arithmetic/data-contract assertion, not complete runtime or native setter coverage.

| Scenario category | Executable frozen scenario | Specified but not executed | Open |
| --- | ---: | ---: | ---: |
| positive | 25 | 0 | 60 |
| negative | 31 | 0 | 54 |
| boundary | 6 | 79 | 0 |
| missing_source | 10 | 0 | 75 |

Each absent scenario retains its own record and reason. A boundary narrative is not converted into an executed test. Extend coverage by adding explicit input mutations and expected decisions against the existing owner, preserving stable case identities and recording new case identities separately when genuinely needed.

### Historical populations and the 44-record discrepancy

The 73 original controls, 73 primary examples, 333 recipe assertions, 467-case PDF V2 bank and its separate 333-comparison subset, 44 historical production comparisons, 94 DAG nodes, 22 registered stages, and actual project instances are not one count. The 44 partially mapped recipe labels are also unrelated to the 44 historical production comparisons.

The preserved static `docs/VS26_GOLDEN_REGRESSION.json` has 13 numerical matches, 27 insufficient-source records and 4 interpretation differences. The later EV-GOLDEN ledger, at implementation commit `85e720d18683a71737c1919d32e393c9d903737b`, reports 15, 25 and 4. Both contain 44 records, but they represent different evidence states. The report needed to reconcile the later record-by-record change is not available in the inspected source set. The files are retained with distinct hashes. Neither is a new execution, and the three current primitive comparisons replace neither set.

### Reproduction and integration commands

From the package root, use the documented environment and commands below. The first checker requires `jsonschema`; the independent arithmetic tools use only Python's standard library. Store new execution records under new names so delivered records remain immutable.

```bash
python tools/validate_delivery.py --root . --self-test --output evidence/LOCAL_DOCUMENT_VALIDATION.json
python tools/verify_golden_arithmetic.py --bank GOLDEN_CASES.json --output evidence/LOCAL_GOLDEN_ARITHMETIC.json
python tools/verify_priority_chain.py --fixture PRIORITY_CHAIN.json --output evidence/LOCAL_PRIORITY_CHAIN.json
```

Use the optional read-only local inspector before integration:

```bash
python tools/inspect_local_binding.py --repo /path/to/current/YENI --mapping CHECK_MAPPING.json --output /private/path/LOCAL_BINDING.json
```

That record captures actual local HEAD, branch, dirty/untracked relevant files, hashes and mapped symbol observations. Matching names or bytes do not automatically become a semantic or engineering approval. Review changed implementations against the existing owners; preserve unfinished work.

The narrow production comparator requires an explicitly reviewed source checkout and its fetch manifest:

```bash
python tools/compare_existing_owners.py --repo /path/to/pinned/YENI --bank GOLDEN_CASES.json --manifest /private/path/FETCH_MANIFEST.json --output evidence/LOCAL_OWNER_COMPARISONS.json
```

Do not bypass hash guards to make a newer local tree appear equivalent. Establish a new reviewed binding and retain both versions. Then extend actual-owner comparisons, keep the protected 44 regression, replay a frozen project through the existing runner, and perform the live acceptance plan through the existing ETABS session when available. No file in this delivery creates another production connection or calculation owner.

## Appendix F — Sources, preservation and private evidence

### Source registry

The following hashes identify the original private source bytes. They are reproducibility identifiers, not public download links. Full PDF/cell/atlas locators are retained per case in GOLDEN_CASES.json; original source access details and raw documents remain separate.

| Source | Original filename | SHA-256 |
| --- | --- | --- |
| GE-S01 | TBDY_PDF_Golden_V2_Manifest.json | `1de835eae29246546cb6ece6255663757c9c00ab82358bcd8fe4f0d4bb2c8914` |
| GE-S02 | 2.pdf | `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31` |
| GE-S03 | PIPELINE_UNIFICATION_20261115.md | `177ce572ab06d9705569e744dcd9e40684bf35d88a568e1d6b9e8f7c76a6a36d` |
| GE-S04 | ex_Hesap_Raporu6.pdf | `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9` |
| GE-S05 | col1.docx | `75e14b85d28958e13b59e77cf12242ef6bf2546492754cd33ac9b900e45fc0de` |
| GE-S06 | 07_GORELI_KAT_OTELEME_KONTROLU.xlsx | `0ec41c2ac49dda5c1ce818f1a282f3212283c0d7e3bf24689925b21b9b5381e4` |
| GE-S07 | 4_sikistirilmis_10MB_alti(1).pdf | `0c6955496aaaa92e2b508ca4eb040927ac8eab2bef92a857f2ff602b8a78fba2` |
| GE-S08 | 17_DUZENSIZLIKLER.xlsx | `3fde2d386c5afb02c30ee895146926f677385bd6f5a726dd1fd5de67a4d0ffad` |
| GE-S09 | 20180318M1-2-1.pdf | `8d3a9a463d4a534ec2c6834c557b5f706e2ad976c2d6837f6c9b6242e38a6bb2` |
| GE-S10 | 14_PERDE_DEVRILME_MOMENT_KONTROLU.xlsx | `aeecc15fa9c22694db31b35f61ac28fac60aa1cccaf17fc77aec6b04342354dd` |
| GE-S11 | sway1.docx | `6e8863ae52834af5febbdd30db0648de186a713f7da991e05db660bb2425b0d7` |
| GE-S12 | exact_bar_hole_hand_resultants.json | `464b3ace47b4f9b532ae0782f1f86ab51a05919df7b400510b6b0f3df93a4707` |
| GE-S13 | 09_KOLON_KESME_KONTROLLERI.xlsx | `a5e2066de1b944c8fc5b686a8ae40e02b23bbed45f46b2f7adbab564b565f811` |
| GE-S14 | strongcol1.docx | `66d596e98139b227b7ac6f8ce7b992ecf52d9110793b9da2624e5968d4be8f4d` |
| GE-S15 | 08_KIRIS_KESME_KONTROLLERI.xlsx | `d061457ac341385a026b830464dc506f006f6a0ca71c92c8cc8feade344f7008` |
| GE-S16 | TS500.pdf | `d925114d01a1de2baee63738bc0da0112b547b58526c3394843c36ee66722d44` |
| GE-S17 | ETEX_ORNEK_RAPOR.pdf | `4650693c95cb69860368efa5d9041a3da61b1d2aa6c5f7d26c6cb55631247f4b` |
| GE-S18 | Hesap_rapor.pdf | `0687b4798a6c10b0a876bfc77f8789eab0a7b356fe4afae4f29ec3de10aed812` |

### Public normative and manufacturer references

- **N1** — [TBDY2018 official publication](https://www.resmigazete.gov.tr/eskiler/2018/03/20180318M1-2.htm). Documented version: TBDY2018. Evidence: RETRIEVED_IN_CURRENT_REVIEW.
- **N1-AFAD** — [AFAD official TBDY publication index](https://afad.gov.tr/turkiye-bina-deprem-yonetmeligi). Documented version: TBDY2018. Evidence: RETRIEVED_IN_CURRENT_REVIEW.
- **N2** — TS500 supplied edition; private source GE-S16. Documented version: February2000; T1/2001 and T2/2002 as present in the supplied copy. Evidence: PRESERVED_FROM_PRIOR_RECIPE_REVIEW.
- **N3** — [CSI Load Combination Data Form](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Combinations/Load_Combination_Data_Form.htm). Documented version: Online help. Evidence: PRESERVED_FROM_PRIOR_RECIPE_REVIEW.
- **N4** — [CSI FrameForce API](https://docs.csiamerica.com/help-files/etabs-api-2016/html/87689f3e-4175-1627-618b-c4ebae5e89b5.htm). Documented version: ETABS2016 API documentation. Evidence: PRESERVED_FROM_PRIOR_RECIPE_REVIEW.
- **N5** — [CSI Frame Output Stations](https://docs.csiamerica.com/help-files/etabs/Menus/Assign/Frame/Frame_Output_Stations.htm). Documented version: Online help. Evidence: PRESERVED_FROM_PRIOR_RECIPE_REVIEW.
- **N6** — [CSI Response Spectrum](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Cases/Response_Spectrum.htm). Documented version: Online help. Evidence: RETRIEVED_IN_CURRENT_REVIEW.
- **N6-SUM** — [CSI Base reactions for response-spectrum analysis](https://web.wiki.csiamerica.com/wiki/spaces/kb/pages/2003704/Base%2Breactions%2Bfor%2Bresponse-spectrum%2Banalysis). Documented version: Online knowledge base. Evidence: RETRIEVED_IN_CURRENT_REVIEW.
- **N7** — [CSI Initial P-Delta Analysis](https://docs.csiamerica.com/help-files/etabs/Menus/Analyze/Set_Analysis_Options/Initial_P-Delta_Analysis.htm). Documented version: Online help. Evidence: RETRIEVED_IN_CURRENT_REVIEW.
- **N8** — [CSI Select Design Combinations](https://docs.csiamerica.com/help-files/etabs/Menus/Design/Select_Design_Combinations.htm). Documented version: Online help. Evidence: PRESERVED_FROM_PRIOR_RECIPE_REVIEW.
- **N9** — [CSI Results](https://docs.csiamerica.com/help-files/etabs-api-2016/html/02e37e34-9c7a-0acc-abaf-39d6c6d96c49.htm). Documented version: ETABS2016 API documentation. Evidence: PRESERVED_FROM_PRIOR_RECIPE_REVIEW.
- **N9-SELECT** — [CSI SetComboSelectedForOutput](https://docs.csiamerica.com/help-files/etabs-api-2016/html/ae0b8d88-44e1-a9ce-ff8b-91bce01f6b0f.htm). Documented version: ETABS2016 API documentation. Evidence: PRESERVED_FROM_PRIOR_RECIPE_REVIEW.
- **N10** — [CSI Load Combinations](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Combinations/Load_Combinations.htm). Documented version: Online help. Evidence: PRESERVED_FROM_PRIOR_RECIPE_REVIEW.
- **N11** — [CSI Combo Interface](https://docs.csiamerica.com/help-files/etabs-api-2016/html/0017cc53-cbcd-b3ca-297d-3c092580b6e0.htm). Documented version: ETABS2016 API documentation. Evidence: PRESERVED_FROM_PRIOR_RECIPE_REVIEW.
- **N11-GET** — [CSI GetCaseList](https://docs.csiamerica.com/help-files/etabs-api-2016/html/c46d4ff6-a816-f7ea-4b74-3eed6bf68e15.htm). Documented version: ETABS2016 API documentation. Evidence: PRESERVED_FROM_PRIOR_RECIPE_REVIEW.
- **N12** — [CSI SetCaseList](https://docs.csiamerica.com/help-files/etabs-api-2016/html/f6569f31-e57a-a342-2adb-4df42f865e76.htm). Documented version: ETABS2016 API documentation. Evidence: RETRIEVED_IN_CURRENT_REVIEW.
- **N12-DELETE** — [CSI DeleteCase](https://docs.csiamerica.com/help-files/etabs-api-2016/html/8f36acb6-5cb2-904b-7159-a4ecb4fab4b4.htm). Documented version: ETABS2016 API documentation. Evidence: RETRIEVED_IN_CURRENT_REVIEW.
- **N13** — [CSI SetModelIsLocked](https://docs.csiamerica.com/help-files/etabs-api-2016/html/74ad467d-fcd7-26a6-1a67-ad5a59c570c9.htm). Documented version: ETABS2016 API documentation. Evidence: PRESERVED_FROM_PRIOR_RECIPE_REVIEW.
- **N14** — [CSI Linear Static](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Cases/Linear_Static.htm). Documented version: Online help. Evidence: PRESERVED_FROM_PRIOR_RECIPE_REVIEW.

### Preservation and distribution

The original source texts, bank, assertion targets and atlas remain unchanged in the private evidence set. The public JSON source manifest includes a preservation index and 142 pinned source-file hash records; it does not expose private access links. Exact source paths/functions in the mapping are evidence about the pinned commit, not substitute implementations for local work.

The public package is suitable for documentation and integration review. The separate private evidence package contains raw documents, databases, atlas, original artifacts and access records. Historical receipt paths that could not be materialized remain marked NOT_AVAILABLE in that private index. Their existence in a prior ledger is not proof that their underlying bytes were inspected here.

PDF and DOCX are readable renderings of this Markdown recipe. JSON mappings and evidence records retain machine-readable precision, stable identities and hashes. Document delivery closes zero engineering checks.
