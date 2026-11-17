/* Presentation of one explicitly selected offline bank. No engineering arithmetic. */
(() => {
  'use strict';
  const el = id => document.getElementById(id);
  const run = el('columnRun'), member = el('columnMember'), loadCase = el('columnCase');
  const view = el('columnView'), proposal = el('columnProposal');
  const beamProposal = el('columnBeamProposal');
  if (typeof sourceQuery !== 'undefined') {
    const requestedView = sourceQuery.get('column_view');
    if ([...view.options].some(option => option.value === requestedView)) view.value = requestedView;
  }
  const labels = {
    STATIC_LINEAR_ADD:'Static Linear Add', RESPONSE_SPECTRUM_LINEAR_ADD:'Linear Add with spectral contribution',
    ENVELOPE:'Envelope', STATIC_NESTED_UNVERIFIED:'Nested static combination · unverified',
    DEFINITION_UNRESOLVED:'Unresolved definition', NON_LINEAR_ADD_ROUTE:'Other combination operator',
    OTHER_ANALYSIS_CASE:'Other analysis type', UNIQUE_STATIC_SOURCE_LINK:'Unique static source link',
    MULTIPLE_NATIVE_STATES:'Multiple force states', AMBIGUOUS_DESIGN_STATION:'Duplicate design station',
    EXACT_NATIVE_STATION_NOT_FOUND:'No exact station match', SOURCE_REFERENCE_ONLY:'Source reference only',
    DESIGN_MEMBER_CONTEXT_UNRESOLVED:'Column and section identity conflict', COMBINATION_NOT_DEFINED:'Missing combination definition',
    DESIGN_STATION_INVALID:'Invalid station', N_COMPRESSION_MAX:'Maximum compression', N_TENSION_MAX:'Maximum tension',
    M2_ABS_MAX:'Maximum |M2|', M3_ABS_MAX:'Maximum |M3|', V2_ABS_MAX:'Maximum |V2|',
    V3_ABS_MAX:'Maximum |V3|', T_ABS_MAX:'Maximum |T|',
    REQUIRED_AREA_BOUNDS_CALCULATED:'Area bounds calculated', NOT_PROVEN:'Unverified',
    NUMERICAL_MATCH:'Matches source', NUMERICAL_MISMATCH:'Source mismatch',
    BELOW_REFERENCE:'Below reference', AT_OR_ABOVE_REFERENCE:'Meets reference',
    NONCOMPRESSION_NOT_APPLICABLE:'Non-compression', PROPOSED_GEOMETRY_CALCULATED:'Proposed geometry',
    WITHIN_SCENARIO_SURFACE:'Within conditional surface', EXCEEDS_SCENARIO_SURFACE:'Conditional surface exceeded',
    NUMERIC_UNRESOLVED:'Numerical solution unresolved', BLOCKED_INPUTS:'Missing inputs',
    NUMERICAL_COMPARISON_MATCH:'Within tolerance', NUMERICAL_COMPARISON_MISMATCH:'Outside tolerance',
    REFERENCE_UNRESOLVED:'Reference solution unresolved', REFERENCE_NOT_STABLE:'Reference solution unstable',
    AXIAL_ONLY_SCENARIO:'Axial-only scenario', OUTSIDE_SCENARIO_AXIAL_RANGE:'Axial scenario limit exceeded',
    WITHIN_1_TO_4_PERCENT_REFERENCE:'Within 1–4%', OUTSIDE_1_TO_4_PERCENT_REFERENCE:'Outside 1–4%',
    ANGULAR_REFINEMENT_NOT_STABLE:'Insufficient angular convergence', AGGREGATE_NOT_BOUND:'Aggregate data pending',
    NEAR_NUMERICAL_SURFACE_BOUNDARY:'Within numerical uncertainty band',
    PROPOSED_TRANSVERSE_REFERENCES_CALCULATED:'Proposed confinement calculation',
    SHEAR_REFERENCES_CALCULATED:'Both shear scenarios calculated', SHEAR_REFERENCE_PARTIAL:'Partial shear scenario',
    WITHIN_REFERENCE_RESISTANCE:'Within reference strength', EXCEEDS_REFERENCE_RESISTANCE:'Reference strength exceeded',
    OUTSIDE_CRACKING_FORMULA_DOMAIN:'Tension lies outside the formula domain',
    ENCLOSED:'Confined · centered scenario', UNENCLOSED:'Unconfined · centered scenario',
    JOINT_GEOMETRIC_REFERENCES_CALCULATED:'Geometric reference calculated',
    NO_RECORDED_BEAM_AT_NODE:'No recorded beam at joint',
    JOINT_OTHER_INCIDENT_FRAME_NOT_CLASSIFIED:'Unclassified connected member',
    JOINT_INTERIOR_FRAME_CONNECTION_NOT_BOUND:'Interior member connection unresolved',
    JOINT_COINCIDENT_DISTINCT_POINT_IDS:'Distinct joints at the same coordinates',
    EQ71_BASELINE_REFERENCES_CALCULATED:'Confinement reference from Eq. (7.1)',
    SAME_CASE_SOURCE_LINKED:'Source records linked in one combination', PARTIAL_SOURCE_LINK:'Partial source link',
    RECORDED_PDELTA_STIFFNESS:'Recorded P-Delta stiffness',
    RECORDED_NONLINEAR_CASE_UNRESOLVED:'Recorded Nonlinear Case · initial conditions unresolved',
    RECORDED_STIFFNESS_SETTING:'Recorded stiffness setting',
    STIFFNESS_PARAMETER_FAMILY_CALCULATED:'Explicit stiffness scenarios',
    SOURCE_LENGTH_REFERENCES_CALCULATED:'Mathematical length references',
    POSITIVE_SOURCE_DENOMINATOR:'Positive source denominator', NONPOSITIVE_SOURCE_DENOMINATOR:'Zero or negative source denominator',
    NUMERICALLY_NEAR_ZERO:'Numerically near zero',
    RECORDED_AXIAL_VALUES_DIFFER:'Recorded N values differ', RECORDED_AXIAL_VALUES_EQUAL:'Recorded N values agree'
  };
  let epoch = 0, historyEpoch = 0, opened = false, offset = 0, total = 0;
  const text = (tag, value, css) => {
    const node = document.createElement(tag); node.textContent = String(value ?? '—');
    if (css) node.className = css;
    return node;
  };
  const show = value => Array.isArray(value) ? value.join(', ') : String(value ?? '—');
  const rounded = value => typeof value === 'number' && Number.isFinite(value) ? Number(value.toPrecision(6)) : null;
  function cageDrawing(cage, layout = null) {
    const box = document.createElement('figure');
    const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
    const make = (tag,attrs) => {
      const node = document.createElementNS('http://www.w3.org/2000/svg',tag);
      for (const [key,value] of Object.entries(attrs)) node.setAttribute(key,String(value));
      svg.append(node); return node;
    };
    const w=cage.t3_mm,h=cage.t2_mm; // Native T3 is the local-2 extent.
    svg.setAttribute('viewBox',`${-w/2-60} ${-h/2-60} ${w+120} ${h+120}`);
    svg.setAttribute('width','190'); svg.setAttribute('height','190');
    svg.setAttribute('role','img'); svg.setAttribute('aria-label',cage.label+' proposed section. Local 2 points right and local 3 points up.');
    make('rect',{x:-w/2,y:-h/2,width:w,height:h,fill:'#edf1f6',stroke:'#64748b','stroke-width':3});
    if (layout) for (const leg of layout.legs) {
      const [a,b] = leg.endpoints_mm;
      make('line',{x1:a[0],y1:-a[1],x2:b[0],y2:-b[1],stroke:'#34786b','stroke-width':leg.diameter_mm,
        'stroke-dasharray':leg.kind==='CROSSTIE' ? '12 6' : 'none'});
    }
    for (const bar of cage.bars) make('circle',{cx:bar.x2_mm,cy:-bar.x3_mm,r:bar.diameter_mm/2,fill:'#214e78'});
    box.append(svg,text('figcaption',`${cage.label} · As ${rounded(cage.as_cm2)} cm² · cover to bar center ${cage.center_offset_mm} mm`));
    if (layout) box.append(text('p','Stirrup and crosstie centerlines. Hooks and vertical detailing require verification.','micro'));
    return box;
  }
  function table(columns, rows) {
    const node = document.createElement('table'); node.className = 'modal-source-table';
    const head = document.createElement('thead'), header = document.createElement('tr');
    columns.forEach(([, label]) => header.append(text('th', label))); head.append(header);
    const body = document.createElement('tbody');
    rows.forEach(row => {
      const tr = document.createElement('tr');
      columns.forEach(([key,, render]) => {
        const cell = text('td', render ? '' : show(row[key]));
        if (render) cell.append(render(row));
        tr.append(cell);
      }); body.append(tr);
    });
    node.append(head, body); return node;
  }
  function displayNumber(value, digits = 2) {
    if (value === null || value === undefined) return '—';
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error('Invalid numerical value in summary.');
    return new Intl.NumberFormat('en-GB', {minimumFractionDigits:digits, maximumFractionDigits:digits, signDisplay:'negative'}).format(value);
  }
  function pmmText(pm) {
    if (pm.status === 'AXIAL_RANGE_EXCEEDED') return `Axial limit exceeded · ${pm.axial_outside_count} records`;
    if (pm.status === 'NO_STATIC_STATES') return 'No static calculation records';
    let value = pm.representative_basis === 'MAXIMUM_RESOLVED_RADIAL_PMM' ? displayNumber(pm.maximum_resolved_utilization,4)+' · conditional' :
      pm.representative_basis === 'MAXIMUM_AXIAL_ONLY_REFERENCE' ? 'Axial only: '+displayNumber(pm.maximum_axial_utilization,4) : 'Numerical result pending';
    if (pm.unresolved_count || pm.blocked_count) value += ` · ${pm.unresolved_count} unresolved / ${pm.blocked_count} missing`;
    if (pm.axial_only_count && pm.representative_basis === 'MAXIMUM_RESOLVED_RADIAL_PMM') value += ` · plus ${pm.axial_only_count} axial-only`;
    if (pm.status_counts.EXCEEDS_SCENARIO_SURFACE) value += ' · surface exceeded';
    return value;
  }
  const shearText = {SOURCE_REFERENCE_EXCEEDED:'Source limit exceeded', PARTIAL_SHEAR_REFERENCES:'Partial source calculation',
    CONDITIONAL_SHEAR_REFERENCES:'Conditional source calculation', NO_STATIC_STATES:'No static records'};
  function overviewDetails(row, scenario) {
    const target = el('columnOverviewDetails'), pm = scenario.pmm, sh = scenario.shear;
    const details = (title, ...nodes) => {
      const item = text('details','');item.append(text('summary',title),...nodes);target.append(item);return item;
    };
    const states = pm.critical_states.map(s => ({...s.native_key,...s.source_values,
      station:displayNumber(s.native_key.ObjSta,3), n:displayNumber(s.source_values.n_compression_kn),
      m2:displayNumber(s.source_values.m2_knm),m3:displayNumber(s.source_values.m3_knm)}));
    details(`${row.member_id} · ${scenario.candidate_label} · PMM scope and critical records`,
      text('p',`${pm.static_state_count} static records: ${pm.radial_pmm_count} radial PMM, ${pm.axial_only_count} axial-only, `+
        `${pm.axial_outside_count} above the axial limit, ${pm.unresolved_count} unresolved, ${pm.blocked_count} missing.`, 'small'),
      table([['LoadCase','Combination'],['station','Station (m)'],['Elm','Analysis element'],['n','N (kN)'],['m2','M2 (kN·m)'],['m3','M3 (kN·m)']],states));
    details('Shear scenarios and governing source states',
      text('p','Shear maxima use all filtered static records. Each direction and concrete contribution branch has its own combination and station. Design Ve remains unverified.','small'),
      table([['axis','Direction'],['branchLabel','Scenario'],['coverage','Resolved / expected'],['ratio','Maximum |V|/Vr'],['cases','Critical combinations']],
        sh.branches.map(b=>({...b,branchLabel:b.branch==='ts500'?'TS500':'Vc=0',coverage:`${b.numeric_count} / ${b.state_count}`,
          ratio:displayNumber(b.maximum_source_utilization,4),cases:[...new Set(b.critical_source_states.map(s=>s.native_key.LoadCase))].join(', ')}))),
      text('h3','Shear for the displayed PMM state'),
      table([['axis','Direction'],['source','Signed V (kN)'],['ts','TS500 |V|/Vr'],['zero','Vc=0 |V|/Vr']],
        sh.at_pmm_representative.map(s=>({axis:s.shear_axis,source:displayNumber(s.native_values[s.shear_axis]),
          ts:displayNumber(s.calculation?.branches.ts500.source_utilization,4),
          zero:displayNumber(s.calculation?.branches.zero_concrete.source_utilization,4)}))));
    if (sh.other_limit_findings.length) details('Additional source findings for shear upper limits',
      text('p','Design Ve and regulatory column applicability remain open.','small'),
      table([['axis','Direction'],['referenceLabel','Reference'],['case','Combination'],['v','Signed V (kN)'],['limit','Limit (kN)']],
        sh.other_limit_findings.map(f=>({...f,referenceLabel:f.reference==='ts500_web'?'TS500 web':'TBDY brittle shear',
          case:f.native_key.LoadCase,v:displayNumber(f.source_signed_v_kn),limit:displayNumber(f.reference_limit_kn)}))));
    const second = row.second_order;
    details('Second order · Inputs and sensitivity references',
      text('p','Verification is pending for ln, k, lk, Cm, β, and magnified moments. '+
        `${second.reference_count} sensitivity comparisons, of which ${second.nonpositive_reference_count} have a near-zero or negative denominator. `+
        'This count describes assumed length and stiffness scenarios. Actual stability requires verified inputs.','small'),
      table([['case','Combination'],['axis','Axis'],['rm','Rm scenario'],['lambda','lk/i reference'],['denominator','Denominator']],
        second.reference_findings.map(r=>({case:r.native_key.LoadCase,axis:r.axis,rm:displayNumber(r.rm_scenario,1),
          lambda:r.lk_over_i_reference,denominator:displayNumber(r.source_denominator,4)}))));
    const c=row.station_coverage;
    details('ETABS design summary · Station matches',text('p',
      `${c.design_row_count} rows / ${c.reference_count} role references. ${c.ambiguous_row_count} ambiguous rows with ${c.ambiguous_reference_count} references. `+
      `${c.missing_exact_reference_count} references without an exact station. The groups overlap at ${c.overlap_reference_count} references, with ${c.union_reference_count} in either group. `+
      'Row and reference counts are reported separately. Station matches require exact identity.','small'));
    details('Full precision and source identifiers',text('pre',JSON.stringify({member_id:row.member_id,scenario,
      second_order:second,station_coverage:row.station_coverage},null,2)));
  }
  function renderOverview(report, page, selectedProposal) {
    const overview = report.column_overview;
    el('columnDemandSummary').replaceChildren();
    const classes=overview.source_combination_classifications;
    el('columnDemandSummary').append(text('p',`${classes.STATIC_LINEAR_ADD || 0} direct static combinations · `+
      `${classes.RESPONSE_SPECTRUM_LINEAR_ADD || 0} spectrum combinations awaiting a verified design vector. `+
      `${overview.member_count} columns · ${overview.members_without_static_states} without a static calculation for this filter.`));
    el('columnUnits').textContent = 'N, M2, and M3 come from the same critical source record. Compression is positive. Force is in kN and moment in kN·m. '+
      'Verified Nd/M2d/M3d and magnified moments are pending. Critical selection uses full precision.';
    const rows = page.rows.map(row => {
      const s=row.scenarios.find(s=>s.candidate_label===selectedProposal);
      if (!s || s.selected_design !== false || s.final_design_eligible !== false || s.design_values?.status !== 'NOT_PROVEN' ||
          ['Nd_kn','M2d_knm','M3d_knm'].some(k=>s.design_values[k]!==null) || row.second_order.actual_second_order_applied!==false ||
          row.second_order.actual_stability_failure_proven!==false) throw new Error('Conditional scenario coverage does not match the summary.');
      const pm=s.pmm, source=pm.representative, v=source?.source_values;
      if (member.value === row.member_id) overviewDetails(row,s);
      return {member_id:row.member_id,story:row.story,combo:(source?.native_key.LoadCase || '—')+
        (pm.critical_state_count>1 ? ` · ${pm.critical_state_count} tied records` : ''),
        n:displayNumber(v?.n_compression_kn),m2:displayNumber(v?.m2_knm),m3:displayNumber(v?.m3_knm),
        proposal:selectedProposal,pmm:pmmText(pm),shear:(shearText[s.shear.status] || 'Coverage unresolved')+' · Ve pending',
        second:'Inputs pending'};
    });
    el('columnForces').append(table([['member_id','Column'],['story','Story'],['combo','Critical static combination'],
      ['n','Source N (kN)'],['m2','Source M2 (kN·m)'],['m3','Source M3 (kN·m)'],['proposal','Reinforcement scenario'],
      ['pmm','Conditional PMM'],['shear','Shear'],['second','Second order'],['member_id','Details',r=>{
        const button=text('button','Inspect');button.type='button';button.setAttribute('aria-label','Inspect column '+r.member_id);
        button.addEventListener('click',()=>{member.value=r.member_id;offset=0;load();});return button;
      }]],rows));
    const c=overview.station_coverage;
    const coverage=text('details','');coverage.append(text('summary','Summary coverage and station matches'),text('p',
      `${c.reference_count} role references: ${c.missing_exact_reference_count} without an exact match, ${c.ambiguous_reference_count} ambiguous station references. `+
      `Intersection ${c.overlap_reference_count}, combination ${c.union_reference_count} · Ambiguous design row ${c.ambiguous_row_count}.`, 'small'));
    el('columnOverviewDetails').append(coverage);
  }
  function options(target, values, placeholder) {
    target.replaceChildren();
    const first = text('option', placeholder); first.value = ''; target.append(first);
    values.forEach(([value, label]) => { const option = text('option', label); option.value = value; target.append(option); });
    target.value = '';
  }
  function renderQuality(quality, page) {
    el('columnUnits').textContent = 'Radial capacities are in kN·m. The comparison uses the maximum resolved primary PMM case per column and proposal and retains all ties.';
    el('columnContext').append(text('p',`${quality.comparison_count} critical records / ${quality.filtered_primary_assessment_count} filtered PMM evaluations. `+
      'The independent numerical comparison covers this critical subset. Full-population coverage and independent critical selection are unverified.'));
    el('columnContext').append(text('p','The primary capacity is the strain-compatible equilibrium point at fixed N and source moment direction. '+
      'Axial residual ≤1 N and directional residual ≤0.001 kN·m. Angular samples bracket the root.','micro'));
    el('columnContext').append(text('p','Both solvers use the same material model. The comparison tests numerical agreement within tolerance. ' +
      'The seismic design vector, second-order effects, and final reinforcement are pending.','micro'));
    const statusCounts=Object.entries(quality.status_counts).map(([status,count])=>`${labels[status] || status}: ${count}`).join(' · ');
    el('columnContext').append(text('p',statusCounts || 'No comparable critical radial records for the selected filter.'));
    for (const row of page.rows) {
      if (row.final_design_eligible !== false || !labels[row.status] || !row.state_id || !row.candidate_id) {
        throw new Error('Numerical comparison record coverage mismatch.');
      }
      const root=row.primary_direction_root,point=root?.point,v=row.native_values;
      const magnitude=Math.hypot(v.M2,v.M3),u2=Math.abs(v.M2)/magnitude,u3=Math.abs(v.M3)/magnitude;
      const capacity=point?.m2_nmm*u2+point?.m3_nmm*u3;
      const cross=point?.m2_nmm*u3-point?.m3_nmm*u2;
      if (!root || root.status !== 'MOMENT_DIRECTION_ROOT_RESOLVED' || root.reason !== null ||
          root.method !== 'BRACKETED_BISECTION_EXACT_AXIAL_EQUILIBRIUM' || root.interpolated_strain_plane_used !== false ||
          root.angle_basis !== 'COMPRESSION_NORMAL_LOCAL2_TO_LOCAL3_FIRST_QUADRANT_DEG' ||
          root.global_root_uniqueness_proven !== false || root.direction_tolerance_nmm !== 1000 ||
          ![v.P,v.M2,v.M3,point?.n_n,point?.m2_nmm,point?.m3_nmm,point?.theta_deg,point?.c_mm,root.target_n_n,root.capacity_nmm,
            root.axial_residual_n,root.direction_residual_nmm,row.primary_capacity_knm,capacity,cross,magnitude].every(Number.isFinite) ||
          magnitude <= 0 || point.c_mm <= 0 || point.theta_deg < 0 || point.theta_deg > 90 ||
          root.axial_residual_n < 0 || root.axial_residual_n > 1 || root.direction_residual_nmm < 0 || root.direction_residual_nmm > 1000 ||
          Math.abs(root.target_n_n+v.P*1000)>1e-6 || Math.abs(point.n_n-root.target_n_n)>1+1e-6 ||
          Math.abs(Math.abs(point.n_n-root.target_n_n)-root.axial_residual_n)>1e-6 ||
          Math.abs(cross)>1000+1e-5 || Math.abs(Math.abs(cross)-root.direction_residual_nmm)>1e-5 ||
          capacity <= 0 || Math.abs(capacity/1e6-row.primary_capacity_knm)>1e-8 ||
          Math.abs(root.capacity_nmm/1e6-row.primary_capacity_knm)>1e-8) {
        throw new Error('PMM equilibrium point source or numerical coverage mismatch.');
      }
      if (row.status.startsWith('NUMERICAL_COMPARISON_') &&
          (!Number.isFinite(row.reference_capacity_knm) || row.reference_capacity_knm <= 0 ||
           !Number.isFinite(row.absolute_difference_knm) || !Number.isFinite(row.comparison_budget_knm) ||
           (row.status === 'NUMERICAL_COMPARISON_MATCH') !== (row.absolute_difference_knm <= row.comparison_budget_knm))) {
        throw new Error('Numerical comparison tolerance status mismatch.');
      }
    }
    el('columnForces').append(table([['member_id','Column'],['story','Story'],['candidate_label','Proposal'],
      ['combo','Critical static combination'],['primary','Ana kapasite'],['reference','Independent capacity'],
      ['delta','|Difference|'],['budget','Tolerance'],['statusText','Numerical comparison']],page.rows.map(r=>({...r,
        combo:r.native_key.LoadCase,primary:displayNumber(r.primary_capacity_knm),reference:displayNumber(r.reference_capacity_knm),
        delta:displayNumber(r.absolute_difference_knm,4),budget:displayNumber(r.comparison_budget_knm,4),statusText:labels[r.status]}))));
    const scope=text('details','');scope.append(text('summary','Coverage and cases outside the comparison'));
    scope.append(table([['member_id','Column'],['candidate_label','Proposal'],['primary_state_count','Primary record'],
      ['primary_radial_state_count','Radial'],['primary_nonradial_state_count','Non-radial'],['target_count','Critical ties'],
      ['states','Primary calculation statuses']],quality.members.map(g=>({...g,states:Object.entries(g.primary_status_counts)
        .map(([s,n])=>`${labels[s] || s}: ${n}`).join(' · ') || 'No static calculation records'}))));
    el('columnOverviewDetails').append(scope);
    const equilibrium=text('details','');equilibrium.append(text('summary','Equilibrium points and approximation differences for critical records'));
    equilibrium.append(text('p','θ is measured from local 2 toward local 3 after reducing the compression normal to the first quadrant using biaxial symmetry.'));
    equilibrium.append(table([['member_id','Column'],['candidate_label','Proposal'],['theta','Compression normal θ (°)'],
      ['depth','c (mm)'],['axial','|ΔN| (N)'],['direction','Directional residual (kN·m)'],['correction','Difference from the coarse minimum (kN·m)']],
      page.rows.map(r=>({...r,theta:displayNumber(r.primary_direction_root.point.theta_deg,5),
        depth:displayNumber(r.primary_direction_root.point.c_mm,5),axial:displayNumber(r.primary_direction_root.axial_residual_n,5),
        direction:displayNumber(r.primary_direction_root.direction_residual_nmm/1e6,6),
        correction:displayNumber(r.primary_root_minus_coarse_minimum_knm,6)}))));
    el('columnOverviewDetails').append(equilibrium);
    if (member.value) {
      const traces=text('details','');traces.append(text('summary','Full precision, source, and solution trace for the selected column'));
      traces.append(text('pre',JSON.stringify({models:quality.reference_models,policy:quality.numerical_policy,comparisons:quality.rows},null,2)));
      el('columnOverviewDetails').append(traces);
    }
  }
  const scwbStatus = {
    BEAM_CAPACITY_NOT_BOUND:'Beam-end reinforcement pending',
    COLUMN_AND_BEAM_INPUTS_INCOMPLETE:'Incomplete column and beam inputs',
    NO_RECORDED_BEAM_IN_DIRECTION:'No recorded beam in this direction',
    TOPOLOGY_UNRESOLVED:'Connection geometry unresolved',
    NO_STATIC_SOURCE_CASES:'No static source case'
  };
  function renderScwb(scwb, page) {
    el('columnDemandSummary').replaceChildren();
    if (scwb.source_population_status === 'BLOCKED_NATIVE_JOINT_GRAPH') {
      el('columnContext').append(text('p',`Joint graph is unverified. ${scwb.selected_column_count} known columns / `+
        `${scwb.expected_column_end_count} expected ends / ${scwb.expected_column_reference_count} expected capacity records. `+
        'Joint count and total coverage are unknown.','warn'));
      el('columnForces').append(table([['member_id','Column'],['end','End']],scwb.unresolved_member_ends));
      const source=text('details','');source.append(text('summary','Open connection source issue'),text('p',scwb.graph_reason));
      el('columnOverviewDetails').append(source);return;
    }
    el('columnUnits').textContent = 'Column capacity sums are in kN·m. Compression N is positive. Physical joint faces require independent identification.';
    el('columnContext').append(text('p',`${scwb.filtered_joint_node_count} joints · ${scwb.static_cases.length} static combinations · `+
      'three reinforcement scenarios · X/Y and both rotation signs. Neighboring members remain in the calculation.'));
    el('columnContext').append(text('p','The displayed minimum covers recorded static cases. The earthquake-compatible minimum Nd still requires verification. '+
      'Verified cage symmetry gives equal column results for both rotation signs. Proposed beam capacities appear in the scenario view. Actual beam capacities and final SCWB remain open.','micro'));
    el('columnContext').append(text('p',Object.entries(scwb.filtered_status_counts)
      .map(([status,count])=>`${scwbStatus[status] || 'Unresolved'}: ${count}`).join(' · ') || 'No joint records.'));
    for (const r of page.rows) {
      if (!scwbStatus[r.status] || !['X','Y'].includes(r.direction) || ![-1,1].includes(r.rotation_sign) ||
          r.final_design_eligible !== false || r.formal_compliance !== 'NOT_PROVEN' || r.normative_exception_applied !== false ||
          r.minimum_over_declared_static_cases_only !== true || r.normative_nd_minimum_proven !== false ||
          r.scwb_ratio !== null || r.normalized_reference_ratio !== null || r.sum_mrb_knm !== null ||
          r.expected_case_count !== scwb.static_cases.length || r.calculated_column_sum_count < 0 ||
          r.calculated_column_sum_count > r.expected_case_count ||
          (r.sampled_minimum_column_sum_knm !== null && (!Number.isFinite(r.sampled_minimum_column_sum_knm) ||
            r.sampled_minimum_column_sum_knm <= 0 || !r.expected_case_count ||
            r.calculated_column_sum_count !== r.expected_case_count || r.topology_reasons.length ||
            !r.sampled_minimum_case_ids.length)) ||
          (r.sampled_minimum_column_sum_knm === null && r.sampled_minimum_case_ids.length) ||
          r.sampled_minimum_case_ids.some(c=>!scwb.static_cases.includes(c))) {
        throw new Error('SCWB summary source coverage or conditional status mismatch.');
      }
    }
    el('columnForces').append(table([['joint_id','Combination'],['elevation','Elevation (m)'],['directionText','Direction and rotation'],
      ['candidate_label','Reinforcement scenario'],['coverage','Column sum / case'],['columnSum','Minimum source ΣMrc (kN·m)'],
      ['cases','Critical static combination'],['state','SCWB durumu']],page.rows.map(r=>({...r,
        elevation:displayNumber(r.elevation_m),directionText:r.direction+' / '+(r.rotation_sign>0?'+':'−'),
        coverage:`${r.calculated_column_sum_count} / ${r.expected_case_count}`,columnSum:displayNumber(r.sampled_minimum_column_sum_knm),
        cases:r.sampled_minimum_case_ids.join(', ') || '—',state:scwbStatus[r.status]}))));
    const roster=text('details','');roster.append(text('summary','Joint members and missing engineering inputs'));
    roster.append(text('p','The ETABS design summary provides required As and reinforcement-area overrides. Actual end reinforcement requires a separate source. '+
      'A zero override conveys no verified reinforcement area. Beam-end capacities, slab contribution, physical faces, seismic Nd, and exceptions are pending.'));
    roster.append(table([['joint','Combination'],['direction','Direction'],['columns','Column ends'],['beams','Beam ends'],['scope','Connection']],
      scwb.nodes.flatMap(n=>['X','Y'].map(direction=>({joint:n.point_id,direction,
        columns:n.rosters[direction].columns.map(c=>`${c.member_id}/${c.end}`).join(', '),
        beams:n.rosters[direction].beams.map(b=>`${b.member_id}/${b.end}`).join(', ') || 'No records',
        scope:n.rosters[direction].reasons.length?'Geometry unresolved':'Native ends linked · physical faces pending'})))));
    el('columnOverviewDetails').append(roster);
    if (member.value) {
      const capacities=text('details','');capacities.append(text('summary','Column capacity records at joints of the selected column'));
      capacities.append(table([['member_id','Column'],['end','End'],['axis','Local moment'],['output_case','Static combination'],
        ['candidate_label','Scenario'],['n','Source N (kN)'],['capacity','Source Mrc (kN·m)']],
        scwb.column_references.map(r=>({...r,n:displayNumber(r.n_source_kn),capacity:displayNumber(r.capacity_knm)}))));
      const traces=text('details','');traces.append(text('summary','Full precision, case, and source identifiers'),
        text('pre',JSON.stringify({column_references:scwb.column_references,beam_sources:scwb.beam_sources,rows:scwb.rows},null,2)));
      capacities.append(traces);el('columnOverviewDetails').append(capacities);
    }
  }
  const beamStatus={BEAM_PROPOSAL_CALCULATED:'Conditional proposal',BEAM_PROPOSAL_BLOCKED:'Inputs or layout unresolved',
    BEAM_PROPOSAL_NUMERIC_UNRESOLVED:'Numerical solution unresolved'};
  const beamReason={BEAM_NATIVE_CUT_AMBIGUOUS:'Native end section unresolved',BEAM_DESIGN_STATION_AMBIGUOUS:'End design station ambiguous',
    BEAM_NATIVE_CUT_NOT_FOUND:'Missing native end section',BEAM_DESIGN_STATION_NOT_FOUND:'Missing end design station',
    BEAM_CONTROL_REFERENCE_NOT_BOUND:'Governing combination unverified'};
  function beamDrawing(profile,cage) {
    const figure=text('figure',''),svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    const b=profile.local3_width_mm,h=profile.local2_height_mm;
    svg.setAttribute('viewBox',`${-b/2-40} ${-h/2-40} ${b+80} ${h+80}`);svg.setAttribute('width','180');svg.setAttribute('height','210');
    svg.setAttribute('role','img');svg.setAttribute('aria-label','Proposed beam section. Local 2 points up and local 3 points right.');
    const shape=(tag,attrs)=>{const node=document.createElementNS('http://www.w3.org/2000/svg',tag);
      for(const [key,value] of Object.entries(attrs))node.setAttribute(key,String(value));svg.append(node);};
    shape('rect',{x:-b/2,y:-h/2,width:b,height:h,fill:'#edf1f6',stroke:'#64748b','stroke-width':3});
    for(const bar of cage.bars)shape('circle',{cx:bar.x3_mm,cy:-bar.x2_mm,r:bar.diameter_mm/2,fill:'#214e78'});
    figure.append(svg,text('figcaption',`Top ${cage.top_label} / Bottom ${cage.bottom_label} · proposed · local 2 points up`));return figure;
  }
  function renderBeams(beams,page,diameter) {
    el('columnDemandSummary').replaceChildren();
    if(beams.source_population_status==='BLOCKED_NATIVE_JOINT_GRAPH') {
      el('columnContext').append(text('p',`Joint graph is unverified. ${beams.known_column_count} known columns retained. Beam and end counts are unknown.`,'warn'));return;
    }
    el('columnUnits').textContent='Areas in mm² and capacities in kN·m. +M3 puts bottom reinforcement in tension, and −M3 puts top reinforcement in tension. N=0 represents pure bending.';
    el('columnContext').append(text('p',`${beams.filtered_bound_end_count}/${beams.filtered_end_count} filtered end-source records. `+
      `Archive contains ${beams.target_beam_count} linked beams / ${beams.expected_end_count} ends; ${beams.calculated_candidate_count}/${beams.expected_candidate_count} reinforcement and capacity scenarios.`));
    el('columnContext').append(text('p','Required As is a target. Top and bottom targets have their own governing combinations. '+
      'N=0 is a beam scenario assumption. Final reinforcement and the SCWB ratio remain unverified.','micro'));
    const profiles=new Map(beams.profiles.map(p=>[p.profile_id,p])),values=[];
    for(const row of page.rows) {
      const c=row.candidates.find(c=>c.diameter_mm===diameter),source=row.source;
      if(!c || row.final_design_eligible!==false || row.formal_compliance!=='NOT_PROVEN' ||
          !['BEAM_END_SOURCE_BOUND','BEAM_END_SOURCE_BLOCKED'].includes(row.status) ||
          row.candidates.length!==3 || new Set(row.candidates.map(x=>x.diameter_mm)).size!==3 ||
          row.candidates.some(x=>![16,20,24].includes(x.diameter_mm) || !beamStatus[x.status] || x.final_design_eligible!==false ||
            x.selected_design!==false || x.physical_cage_proven!==false ||
            (row.status==='BEAM_END_SOURCE_BLOCKED' && (x.status!=='BEAM_PROPOSAL_BLOCKED' || x.capacity!==null)) ||
            (x.status==='BEAM_PROPOSAL_BLOCKED' && x.capacity!==null) ||
            (x.status!=='BEAM_PROPOSAL_BLOCKED' && (row.status!=='BEAM_END_SOURCE_BOUND' || source?.status!=='BEAM_END_SOURCE_BOUND' ||
              source?.native_cut_count!==1 || source?.design_match_count!==1 || source?.targets?.same_force_vector_claimed!==false ||
              source?.targets?.total_required_area_is_provided!==false || !profiles.has(row.profile_id) ||
              ['AsTopCombo','AsBotCombo','TLngCombo'].some(key=>source?.targets?.control_references?.[key]?.status!=='OBSERVED') ||
              x.capacity?.axial_force_scenario_n!==0 || x.capacity?.source_beam_axial_force_applied!==false || x.capacity?.final_design_eligible!==false ||
              (x.status==='BEAM_PROPOSAL_NUMERIC_UNRESOLVED' && x.capacity?.status!=='BEAM_CAPACITY_UNRESOLVED') ||
              (x.status==='BEAM_PROPOSAL_CALCULATED' && (x.capacity?.status!=='BEAM_CAPACITY_REFERENCE' ||
                !Number.isFinite(x.capacity.positive_m3_knm) || x.capacity.positive_m3_knm<=0 ||
                !Number.isFinite(x.capacity.negative_m3_knm) || x.capacity.negative_m3_knm>=0)))))) {
        throw new Error('Beam proposal source or conditional capacity mismatch.');
      }
      const targets=source?.targets,cap=c.status==='BEAM_PROPOSAL_CALCULATED'?c.capacity:null;
      values.push({member_id:row.member_id,end:row.end,station:displayNumber(source?.target_station_m,3),
        topTarget:displayNumber(targets?.top_mm2),bottomTarget:displayNumber(targets?.bottom_mm2),
        top:c.top_label,bottom:c.bottom_label,positive:displayNumber(cap?.positive_m3_knm),negative:displayNumber(cap?.negative_m3_knm),
        state:beamReason[row.reason] || beamStatus[c.status]});
      if(member.value) {
        const detail=text('details','');detail.append(text('summary',`${row.member_id}/${row.end} · End source and proposed layout`));
        if(c.bars?.length && profiles.has(row.profile_id))detail.append(beamDrawing(profiles.get(row.profile_id),c));
        detail.append(text('p',`Top governing combination: ${targets?.top_combination || '—'} · Bottom governing combination: ${targets?.bottom_combination || '—'} · `+
          `native section / design row: ${source?.native_cut_count ?? '—'} / ${source?.design_match_count ?? '—'}`));
        if(row.reason || c.reason)detail.append(text('p',row.reason || c.reason,'warn'));
        const trace=text('details','');trace.append(text('summary','Full precision and source trace'),text('pre',JSON.stringify(row,null,2)));
        detail.append(trace);el('columnOverviewDetails').append(detail);
      }
    }
    el('columnForces').append(table([['member_id','Beam'],['end','End'],['station','Station (m)'],
      ['topTarget','Top target (mm²)'],['bottomTarget','Bottom target (mm²)'],['top','Top proposal'],['bottom','Bottom proposal'],
      ['positive','+M3 (kN·m)'],['negative','−M3 (kN·m)'],['state','Status']],values));
    const scope=text('details','');scope.append(text('summary','Layout assumptions and out-of-scope beams'),
      text('p','ETABS top and bottom covers are measured to the longitudinal bar centroid. The proposal uses 30 mm side clear cover and Φ10 stirrups. '+
        'Single-row spacing considers bar diameter and the 25 mm reference. Aggregate size, anchorage, continuity, torsion and web steel, and slab participation require verification.'),
      table([['member_id','Beam'],['scope','Scope']],beams.outside_joint_scope_beams.map(r=>({...r,scope:'No native end at a recorded column joint'}))));
    el('columnOverviewDetails').append(scope);
  }
  const scenarioStatus={SCENARIO_REFERENCE_SATISFIED:'Meets scenario reference',SCENARIO_REFERENCE_NOT_SATISFIED:'Below scenario reference',
    SCENARIO_BOUNDARY_UNRESOLVED:'Numerical boundary unresolved',SCENARIO_INPUTS_INCOMPLETE:'Missing participant capacity',
    TOPOLOGY_UNRESOLVED:'Connection geometry unresolved',NO_RECORDED_BEAM_IN_DIRECTION:'No recorded beam in direction',NO_STATIC_SOURCE_CASES:'No static column N record'};
  function renderScenarios(scenarios,page) {
    el('columnDemandSummary').replaceChildren();
    if(scenarios.source_population_status==='BLOCKED_NATIVE_JOINT_GRAPH') {
      el('columnContext').append(text('p',`${scenarios.known_column_count} known columns / ${scenarios.expected_column_end_count} expected column ends retained. `+
        'Joint and scenario totals are unknown.','warn'));return;
    }
    el('columnUnits').textContent='Ratio = ΣMrc(column source N) / [1.2 ΣMrb(beam N=0)]. Reference ≥1. Capacities in kN·m.';
    el('columnContext').append(text('p',`${scenarios.filtered_joint_node_count} joints · ${scenarios.filtered_summary_count} joint-direction summaries · `+
      `column ${scenarios.display_column_label} / beam Φ${scenarios.display_beam_diameter_mm}. End bar counts and continuity require independent checks for a common diameter.`));
    el('columnContext').append(text('p','The case filter selects column N records. Beam area envelopes can come from different governing combinations. '+
      'Rotation signs are geometric references. Verification of earthquake-compatible minimum Nd and final SCWB compliance is pending.','micro'));
    for(const row of page.rows) {
      const ratio=row.minimum_normalized_scenario_ratio,complete=ratio!==null;
      if(!scenarioStatus[row.status] || !['X','Y'].includes(row.direction) || row.column_label!==scenarios.display_column_label ||
          row.beam_diameter_mm!==scenarios.display_beam_diameter_mm || row.scwb_ratio!==null || row.final_design_eligible!==false ||
          row.formal_compliance!=='NOT_PROVEN' || row.normative_nd_minimum_proven!==false || row.normative_exception_applied!==false ||
          row.sampled_static_cases_and_both_rotations_only!==true || row.expected_case_rotation_count!==2*scenarios.static_cases.length ||
          row.calculated_case_rotation_count<0 || row.calculated_case_rotation_count>row.expected_case_rotation_count ||
          row.complete_declared_scenario_population!==complete ||
          (complete && (!Number.isFinite(ratio) || ratio<=0 || !row.expected_case_rotation_count ||
            row.calculated_case_rotation_count!==row.expected_case_rotation_count || row.topology_reasons.length ||
            !scenarios.static_cases.includes(row.governing_output_case) || ![-1,1].includes(row.governing_rotation_sign) ||
            !row.governing_result_ids.length || ['governing_sum_mrc_knm','governing_sum_mrb_knm','governing_required_mrc_knm'].some(k=>!Number.isFinite(row[k]) || row[k]<=0))) ||
          (!complete && (row.governing_result_ids.length || row.governing_output_case!==null || row.governing_rotation_sign!==null ||
            ['governing_sum_mrc_knm','governing_sum_mrb_knm','governing_required_mrc_knm'].some(k=>row[k]!==null))) ||
          (row.status==='SCENARIO_REFERENCE_SATISFIED' && (!complete || ratio<1 || row.scenario_reference_satisfied!==true)) ||
          (row.status==='SCENARIO_REFERENCE_NOT_SATISFIED' && (!complete || ratio>=1 || row.scenario_reference_satisfied!==false)) ||
          (row.status==='SCENARIO_BOUNDARY_UNRESOLVED' && (!complete || row.scenario_reference_satisfied!==null)) ||
          (!row.status.startsWith('SCENARIO_REFERENCE_') && row.status!=='SCENARIO_BOUNDARY_UNRESOLVED' && (complete || row.scenario_reference_satisfied!==null))) {
        throw new Error('SCWB proposal case coverage or conditional result mismatch.');
      }
    }
    el('columnForces').append(table([['joint_id','Combination'],['elevation','Elevation (m)'],['direction','Direction'],['coverage','Case × rotation'],
      ['caseText','Governing column N case / rotation'],['columnSum','ΣMrc (kN·m)'],['beamSum','ΣMrb (kN·m)'],
      ['ratio','Conditional ratio ≥1'],['state','Status']],page.rows.map(r=>({...r,elevation:displayNumber(r.elevation_m),
        coverage:`${r.calculated_case_rotation_count}/${r.expected_case_rotation_count}`,
        caseText:r.governing_output_case?`${r.governing_output_case} / ${r.governing_rotation_sign===1?'+':'−'}`:'—',
        columnSum:displayNumber(r.governing_sum_mrc_knm),beamSum:displayNumber(r.governing_sum_mrb_knm),
        ratio:displayNumber(r.minimum_normalized_scenario_ratio,3),state:scenarioStatus[r.status]}))));
    const scope=text('details','');scope.append(text('summary','Joint participants and open engineering conditions'),
      text('p','The check verifies I/J identity, local axes, and the native rotational degree of freedom. Verification is pending for V×r and N×r transfer to the column face, slab contribution, '+
        'actual reinforcement, aggregate, torsion, anchorage, continuity, seismic Nd, and exceptions. X rotation uses the right-hand rule about +Y, and Y about −X.'),
      table([['joint','Combination'],['direction','Direction'],['columns','Column / end'],['beams','Beam / end']],scenarios.nodes.flatMap(n=>['X','Y'].map(d=>({
        joint:n.point_id,direction:d,columns:n.rosters[d].columns.map(r=>`${r.member_id}/${r.end}`).join(', '),
        beams:n.rosters[d].beams.map(r=>`${r.member_id}/${r.end}`).join(', ') || 'No records'})))));
    el('columnOverviewDetails').append(scope);
    if(member.value) {
      const details=text('details','');details.append(text('summary','Beam moment branches at joints of the selected column'));
      details.append(table([['joint_id','Combination'],['dir','Direction / rotation'],['member','Beam / end'],['top_label','Top proposal'],['bottom_label','Bottom proposal'],
        ['face','Tension face'],['moment','Local M3 (kN·m)'],['reason','Open issue']],scenarios.beam_references.map(r=>({...r,
          dir:`${r.direction}/${r.rotation_sign===1?'+':'−'}`,member:`${r.member_id}/${r.end}`,face:({TOP:'Top',BOTTOM:'Bottom'})[r.tension_face],
          moment:displayNumber(r.signed_local_m3_knm)}))));
      const raw=text('details','');raw.append(text('summary','Full precision, I/J, degree of freedom, and case trace'),
        text('pre',JSON.stringify({rows:scenarios.rows,beam_references:scenarios.beam_references,member_moment_mappings:scenarios.member_moment_mappings},null,2)));
      details.append(raw);el('columnOverviewDetails').append(details);
    }
  }
  function clearResult() {
    for (const id of ['columnSummary', 'columnExports', 'columnContext', 'columnForces',
                      'columnReplay', 'columnCoverage', 'columnGaps', 'columnPage',
                      'columnDemandSummary', 'columnDemandRoutes', 'columnUnits', 'columnOverviewDetails']) el(id).replaceChildren();
    el('columnPrevious').disabled = true; el('columnNext').disabled = true;
  }
  function renderSpectral(report, params) {
    const s=report.column_spectral_envelopes, page=report.demand_page;
    const fail=()=>{throw new Error('Spectral envelope source, page, or acceptance scope mismatch.');};
    const components=['P','V2','V3','T','M2','M3'], display=['N','V2','V3','T','M2','M3'];
    const falseFlags=['physical_concurrency_proven','code_rule_qualified','analysis_generation_qualified',
      'additional_directional_factor_applied','spectrum_scale_reapplied','strength_amplification_reapplied',
      'static_candidate_population_changed','final_design_eligible'];
    if(!s || s.schema!=='tbdy.next.column-spectral-envelopes.v1' ||
       s.policy!=='DIRECT_LINEAR_ADD_STATIC_CENTER_RS_SCALAR_RADIUS_V1' || s.source_run_id!==report.run_id ||
       s.source_archive_sha256!==report.source_archive_sha256 || s.source_bank_result_sha256!==report.result_sha256 ||
       !/^[a-f0-9]{64}$/.test(s.result_sha256) || falseFlags.some(k=>s[k]!==false) ||
       s.design_demand_authority!=='DENIED' || s.formal_compliance!=='NOT_PROVEN' || s.engineering_release!=='NOT_READY' ||
       s.absolute_tolerance_native!=='1e-09' || s.relative_tolerance!=='1e-12' ||
       !['NUMERICAL_MATCH','NUMERICAL_MISMATCH','NOT_PROVEN'].includes(s.replay_status) ||
       !['SOURCE_COVERAGE_COMPLETE','PARTIAL','NOT_AVAILABLE'].includes(s.source_coverage_status) ||
       s.analysis_order!=='NOT_PROVEN' || s.units?.force!=='kN' || s.units?.moment!=='kNm' || s.units?.station!=='m' ||
       s.units?.native_p_positive!=='TENSION' || s.units?.display_n_positive!=='COMPRESSION' ||
       JSON.stringify(s.components)!==JSON.stringify(components) || JSON.stringify(s.display_components)!==JSON.stringify(display) ||
       s.member_id_filter!==(member.value || null) || s.output_case_filter!==(loadCase.value || null) ||
       !page || page.view!=='spectral-envelopes' || page.member_id!==s.member_id_filter || page.output_case!==s.output_case_filter ||
       page.offset!==offset || page.limit!==200 || !Number.isInteger(page.total) || page.total<0 || page.total!==s.filtered_pair_count ||
       !Array.isArray(page.rows) || page.rows.length>200 || page.rows.length!==Math.max(0,Math.min(200,page.total-offset))) fail();
    const numeric=value=>typeof value==='number' && Number.isFinite(value);
    const routes=new Map(s.combinations.map(c=>[c.combination,c]));
    for(const row of page.rows) {
      if(!['NUMERICAL_MATCH','NUMERICAL_MISMATCH','SOURCE_UNRESOLVED'].includes(row.status) ||
          row.final_design_eligible!==false || row.concurrent_force_vector!==null ||
          row.station_key?.Obj!==row.member_id || member.value && row.member_id!==member.value ||
          loadCase.value && row.output_case!==loadCase.value || !numeric(row.station_key?.ObjSta) || !numeric(row.station_key?.ElmSta)) fail();
      if(row.status==='SOURCE_UNRESOLVED') {
        if(row.bounds!==null || row.scalar_comparisons!==0 || !row.reason) fail();
      } else {
        const terms=routes.get(row.output_case)?.definition?.terms;
        if(!row.bounds || !row.native_bounds || row.scalar_comparisons!==12 ||
          display.some(c=>!numeric(row.bounds[c]?.lower) || !numeric(row.bounds[c]?.upper) || row.bounds[c].lower>row.bounds[c].upper) ||
          components.some(c=>!numeric(row.center?.[c]) || !numeric(row.spectral_radius?.[c]) || row.spectral_radius[c]<0) ||
          row.bounds.N.lower!==-row.native_bounds.P?.upper || row.bounds.N.upper!==-row.native_bounds.P?.lower ||
          !Array.isArray(row.native_steps) || row.native_steps.length!==2 ||
          new Set(row.native_steps.map(r=>r.native_key?.StepType)).size!==2 ||
          row.native_steps.some(r=>!['Max','Min'].includes(r.native_key?.StepType) || r.native_key.StepNum!==0 ||
            r.native_key.LoadCase!==row.output_case || !r.source_row_id || !r.source_call_id ||
            ['Obj','ObjSta','Elm','ElmSta'].some(k=>r.native_key[k]!==row.station_key[k])) ||
          !Array.isArray(terms) || !Array.isArray(row.source_terms) || row.source_terms.length!==terms.length ||
          row.source_terms.some((r,i)=>r.factor!==terms[i].factor || r.native_key?.LoadCase!==terms[i].name ||
            ![1,4].includes(r.case_type) || r.native_key.StepType!==(r.case_type===4?'Max':'Single Value') || r.native_key.StepNum!==0 ||
            !r.source_row_id || !r.source_call_id || ['Obj','ObjSta','Elm','ElmSta'].some(k=>r.native_key[k]!==row.station_key[k])) ||
          !Array.isArray(row.comparisons) || row.comparisons.length!==12 ||
          new Set(row.comparisons.map(c=>c.step_type+':'+c.component)).size!==12 ||
          row.comparisons.some(c=>!numeric(c.calculated) || !numeric(c.observed) || !numeric(c.absolute_difference) ||
            !components.includes(c.component) || !['Max','Min'].includes(c.step_type) ||
            c.unit!==(['P','V2','V3'].includes(c.component)?'kN':'kNm') ||
            c.absolute_difference<0 || !numeric(c.tolerance) || c.tolerance<=0 || typeof c.match!=='boolean') ||
          (row.status==='NUMERICAL_MATCH')!==row.comparisons.every(c=>c.match)) fail();
      }
    }
    const interval=(row,c)=>row.bounds ? `${displayNumber(row.bounds[c].lower)} / ${displayNumber(row.bounds[c].upper)}` : '—';
    const label=r=>({NUMERICAL_MATCH:'Matches source',NUMERICAL_MISMATCH:'Source mismatch',SOURCE_UNRESOLVED:'Missing source link'})[r.status];
    const details=(target,title,...nodes)=>{const d=text('details','');d.append(text('summary',title),...nodes);target.append(d);};
    el('columnDemandSummary').append(text('p',`${s.eligible_combination_count} spectral combinations · ${s.matched_rows}/${s.expected_native_row_count} matching native rows · ${s.scalar_comparisons} scalar comparisons`));
    el('columnContext').append(text('p','Each component has separate lower and upper bounds. Final design combination, second-order effects, and code applicability are pending.'));
    el('columnContext').append(text('p',`Source coverage: ${s.source_coverage_status} · ${s.unresolved_pair_count} missing pairs · ${s.mismatched_rows} mismatched rows · columns with unknown station coverage: ${s.members_without_station_population.length}.`,'micro'));
    el('columnUnits').textContent='Compression N is positive (kN). M2 and M3 follow local axes (kN·m). Stations are in m. The bounds represent individual components. N lower=−P upper, and N upper=−P lower.';
    el('columnForces').append(table([['member_id','Column'],['story','Story'],['output_case','Combination'],['cut','Element · station (m)'],
      ['n','N lower / upper'],['m2','M2 lower / upper'],['m3','M3 lower / upper'],['label','Numerical source']],page.rows.map(r=>({...r,
        cut:`${r.station_key.Elm} · ${displayNumber(r.station_key.ObjSta,4)}`,n:interval(r,'N'),m2:interval(r,'M2'),m3:interval(r,'M3'),label:label(r)}))));
    details(el('columnOverviewDetails'),'V2, V3, and T bounds',table([['member_id','Column'],['output_case','Combination'],
      ['cut','Element · object / element station (m)'],['v2','V2 lower / upper (kN)'],['v3','V3 lower / upper (kN)'],['t','T lower / upper (kN·m)']],
      page.rows.map(r=>({...r,cut:`${r.station_key.Elm} · ${displayNumber(r.station_key.ObjSta,4)} / ${displayNumber(r.station_key.ElmSta,4)}`,
        v2:interval(r,'V2'),v3:interval(r,'V3'),t:interval(r,'T')}))));
    details(el('columnOverviewDetails'),'Full-precision calculations and source rows for this page',text('pre',JSON.stringify(page,null,2)));
    details(el('columnOverviewDetails'),'Spectrum parameter sources',text('pre',JSON.stringify(s.spectral_cases,null,2)));
    el('columnDemandRoutes').append(table([['combination','Combination'],['recipe','Tarif'],['reason','Reason for exclusion']],
      s.combinations.map(c=>({...c,recipe:c.definition.terms?.map(t=>`${t.factor} × ${t.name}`).join(' + ')}))));
    el('columnReplay').append(text('p','C is the signed static sum. A is Σ |coefficient| × spectral Max amplitude. C−A and C+A are compared against recorded Min/Max. Source coefficients already include the recorded 100%/30%, D, and spectrum scale.'));
    details(el('columnReplay'),'Combination coefficients and numerical tolerances',text('pre',JSON.stringify({
      absolute_tolerance_native:s.absolute_tolerance_native,relative_tolerance:s.relative_tolerance,
      maximum_absolute_difference_by_unit:s.maximum_absolute_difference_by_unit,combinations:s.combinations},null,2)));
    el('columnGaps').append(text('p',`${s.selected_member_count} columns in the acceptance chain from the project design combination and N/M2/M3 to reinforcement and code checks. This view examines scalar force envelopes.`));
    for(const [title,url] of [['HTML report for this page','/report/column-bank?'],['JSON data for this page','/api/export-column-bank?']]) {
      const a=text('a',title);a.href=url+params.toString();a.target='_blank';a.rel='noopener';el('columnExports').append(a);
    }
    total=page.total;
    el('columnPage').textContent=page.rows.length ? `${offset+1}–${offset+page.rows.length} / ${total} pairs of bounds` : 'No records for this filter and view.';
    el('columnPrevious').disabled=offset===0;el('columnNext').disabled=offset+page.limit>=total;
  }
  async function get(url) {
    const response = await fetch(url, {cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Archive verification failed');
    return data;
  }
  function renderSpectralDesign(report, params, selectedView, selectedProposal) {
    const s=report.column_spectral_design, p=report.spectral_pmm, replay=report.spectral_replay, page=report.demand_page;
    const golden=report.golden_regression_gate;
    const fail=()=>{throw new Error('Seismic design view source or scope mismatch.');};
    const hash=x=>typeof x==='string' && /^[0-9a-f]{64}$/.test(x);
    const numeric=x=>typeof x==='number' && Number.isFinite(x);
    const count=x=>Number.isSafeInteger(x) && x>=0;
    const conditional=x=>x && x.final_design_eligible===false && x.normative_qualification==='NOT_PROVEN';
    if(!s || !p || !replay || !page || s.schema!=='tbdy.next.spectral-design-population.v1' ||
       !golden || golden.schema!=='tbdy.next.golden-regression-gate.v1' || !hash(golden.result_sha256) ||
       golden.source_manifest_sha256!=='59dedec19a7e6c3d5f496e8d616b8c708af3c99701e271bd872644e39361bec7' ||
       golden.normative_qualification!=='NOT_PROVEN' || golden.acceptance_eligible!==false ||
       golden.gate_status!=='REQUIRED_REPORT_GOLDEN_COVERAGE_INCOMPLETE' || golden.engineering_release!=='NOT_READY' ||
       p.schema!=='tbdy.next.spectral-pmm-scenarios.v1' || replay.schema!=='tbdy.next.column-spectral-envelopes.v1' ||
       s.source_run_id!==report.run_id || p.source_run_id!==report.run_id || replay.source_run_id!==report.run_id ||
       [s,p,replay].some(x=>x.source_archive_sha256!==report.source_archive_sha256 || !hash(x.result_sha256)) ||
       s.source_bank_result_sha256!==report.result_sha256 || replay.source_bank_result_sha256!==report.result_sha256 ||
       s.source_replay_result_sha256!==replay.result_sha256 || p.source_population_result_sha256!==s.result_sha256 ||
       p.source_static_demand_result_sha256!==s.source_static_demand_result_sha256 ||
       s.permutation_policy!=='CSI_MAX_MIN_P_M2_M3_EIGHT_CORNERS_CONDITIONAL_V1' ||
       s.applicable_design_rule!=='CSI_ETABS_CONCRETE_FRAME_DESIGN_2_1_MAX_MIN_PERMUTATIONS' ||
       p.selection_basis!=='MAX_RESOLVED_RADIAL_RATIO_AMONG_ALL_RECORDED_CUTS_AND_EIGHT_SIGN_CANDIDATES' ||
       p.numerical_policy?.solver_revision!=='VS25_DIRECTION_ROOT' ||
       [s,p].some(x=>!conditional(x) || x.design_demand_authority!=='DENIED' || x.engineering_release!=='NOT_READY' ||
         ['physical_concurrency_proven','analysis_generation_qualified','continuous_axial_envelope_complete','second_order_applied'].some(k=>x[k]!==false)) ||
       s.additional_directional_factor_applied!==false || s.spectrum_scale_reapplied!==false ||
       !count(s.candidate_count) || !count(s.envelope_count) || s.candidate_count!==8*s.envelope_count ||
       p.candidate_count!==s.candidate_count || p.assessment_count!==3*s.candidate_count ||
       p.expected_assessment_count!==3*s.expected_candidate_count ||
       page.view!==selectedView || page.member_id!==(member.value||null) || page.output_case!==(loadCase.value||null) ||
       page.member_id!==s.member_id_filter || page.output_case!==s.output_case_filter || page.column_label!==selectedProposal ||
       s.reinforcement_filter!==selectedProposal || page.offset!==offset || page.limit!==200 || !count(page.total) ||
       page.raw_population_included!==false || !Array.isArray(page.rows) ||
       page.rows.length!==Math.max(0,Math.min(page.limit,page.total-offset))) fail();
    function validateState(r, name) {
      if(!r || !conditional(r) || r.engineering_status!=='CONDITIONAL' || r.second_order_applied!==false ||
        r.member_id!==name || r.station_key?.Obj!==name || !r.station_key?.Elm ||
        !numeric(r.station_key.ObjSta) || r.station_key.ObjSta<0 || !numeric(r.station_key.ElmSta) || r.station_key.ElmSta<0 ||
        r.reinforcement!==selectedProposal || !hash(r.evaluation_id) || !hash(r.candidate_id) ||
        !/^P[+-]1_M2[+-]1_M3[+-]1$/.test(r.sign_id) || !r.combination ||
        (page.output_case!==null && r.combination!==page.output_case) ||
        ['N_kN','M2_kNm','M3_kNm'].some(k=>!numeric(r.forces?.[k])) ||
        (r.conditional_pmm_ratio!==null && (!numeric(r.conditional_pmm_ratio) || r.conditional_pmm_ratio<0)) ||
        !['WITHIN_SCENARIO_SURFACE','EXCEEDS_SCENARIO_SURFACE','AXIAL_ONLY_SCENARIO','OUTSIDE_SCENARIO_AXIAL_RANGE','NUMERIC_UNRESOLVED','BLOCKED_INPUTS'].includes(r.numerical_status) ||
        (['WITHIN_SCENARIO_SURFACE','EXCEEDS_SCENARIO_SURFACE'].includes(r.numerical_status)!==(r.conditional_pmm_ratio!==null))) fail();
    }
    for(const r of page.rows) {
      if(!conditional(r) || r.engineering_status!=='CONDITIONAL' || r.reinforcement!==selectedProposal ||
         (page.member_id!==null && r.member_id!==page.member_id)) fail();
      if(selectedView==='spectral-candidates') {
        validateState(r,r.member_id);
        const c=r.design_candidate, e=r.numerical_evidence;
        if(!c || c.schema!=='tbdy.next.code-design-demand-candidate.v1' || c.candidate_id!==r.candidate_id ||
           c.source_archive_sha256!==s.source_archive_sha256 || c.source_run_id!==s.source_run_id ||
           c.source_replay_result_sha256!==replay.result_sha256 || !hash(c.source_envelope_content_sha256) ||
           c.permutation_policy!==s.permutation_policy || c.applicable_design_rule!==s.applicable_design_rule ||
           c.source_combination!==r.combination || c.sign_id!==r.sign_id || !conditional(c) ||
           c.physical_concurrency_proven!==false || c.second_order_applied!==false ||
           ['Obj','ObjSta','Elm','ElmSta'].some(k=>c.station_key[k]!==r.station_key[k]) ||
           ['N_kN','M2_kNm','M3_kNm'].some(k=>c.forces[k]!==r.forces[k]) ||
           (e===null)!==(r.numerical_evidence_id===null) ||
           (e && (e.solver_revision!=='VS25_DIRECTION_ROOT' || e.N_N!==r.forces.N_kN*1000 ||
             e.M2_Nmm!==r.forces.M2_kNm*1000000 || e.M3_Nmm!==r.forces.M3_kNm*1000000 ||
             e.result.status!==r.numerical_status || e.result.utilization!==r.conditional_pmm_ratio))) fail();
      } else {
        if(r.continuous_axial_envelope_complete!==false || r.selection_scope!=='FINITE_GENERATED_CANDIDATES_ONLY' ||
           !count(r.assessment_count) || !count(r.unresolved_or_axial_outside_count)) fail();
        for(const v of [r.governing_resolved,r.first_unresolved_or_axial_outside].filter(Boolean)) validateState(v,r.member_id);
        if(r.maximum_resolved_conditional_ratio!==(r.governing_resolved?.conditional_pmm_ratio ?? null) ||
          (r.unresolved_or_axial_outside_count>0 && (!r.first_unresolved_or_axial_outside || r.numerical_selection_complete))) fail();
      }
    }
    el('columnDemandSummary').append(text('p',`${replay.eligible_combination_count} combinations with spectral contributions · `+
      `${replay.matched_rows}/${replay.expected_native_row_count} matching Max/Min rows · ${replay.scalar_comparisons} component comparisons.`));
    el('columnContext').append(text('p',`${s.candidate_count}/${s.expected_candidate_count} sign candidates · `+
      `${p.assessment_count}/${p.expected_assessment_count} PMM evaluations · ${s.blocked_pair_count} bound pairs with no eligible candidates.`));
    el('columnContext').append(text('p','The governing ratio is the maximum resolved ratio over this finite candidate set. Intermediate N values remain unverified. '+
      'Second-order effects, minimum eccentricity, reinforcement selection, and TBDY design acceptance are pending.','micro'));
    el('columnContext').append(text('p','Golden report acceptance remains open. The 23+7 legacy report checks are retained. '+
      'Full algorithm verification requires additional evidence.','micro'));
    el('columnUnits').textContent='Conditional design candidate. Compression N is positive (kN). M2 and M3 use local axes (kN·m). Stations are in m. '+
      'Sign scenarios use native tension-positive P, with N=−P. These are component bounds.';
    const rows=page.rows.map(r=>{
      const state=selectedView==='spectral-candidates'?r:r.governing_resolved;
      let status=state ? (labels[state.numerical_status] || state.numerical_status) : 'No resolved radial ratio';
      if(r.unresolved_or_axial_outside_count) status=`${r.unresolved_or_axial_outside_count} unresolved or above the axial limit · `+status;
      else if(selectedView==='spectral-design' && !r.numerical_selection_complete) status='Missing source coverage or numerical selection · '+status;
      return {...r,combo:state?.combination || '—',station:state?`${state.station_key.Elm} · ${displayNumber(state.station_key.ObjSta,4)} / ${displayNumber(state.station_key.ElmSta,4)}`:'—',
        sign:state?.sign_id || '—',n:displayNumber(state?.forces.N_kN),m2:displayNumber(state?.forces.M2_kNm),m3:displayNumber(state?.forces.M3_kNm),
        ratio:displayNumber(state?.conditional_pmm_ratio,4),outcome:status,second:'Pending',critical:state};
    });
    const columns=[['member_id','Column'],['story','Story'],['combo','Governing combination'],['station','Element · object / element station (m)'],
      ['sign','Sign scenario'],['n','N (kN)'],['m2','M2 (kN·m)'],['m3','M3 (kN·m)'],['reinforcement','Proposed reinforcement'],
      ['ratio','Conditional PMM'],['outcome','Numerical status'],['second','Second order']];
    if(selectedView==='spectral-design') columns.push(['member_id','Details',r=>{
      const button=text('button','Open scenarios');button.type='button';
      button.addEventListener('click',()=>{member.value=r.member_id;if(r.critical)loadCase.value=r.critical.combination;
        view.value='spectral-candidates';offset=0;load();});return button;
    }]);
    el('columnForces').append(table(columns,rows));
    const details=(title,...nodes)=>{const d=text('details','');d.append(text('summary',title),...nodes);el('columnOverviewDetails').append(d);};
    details('Golden report verification scope',text('pre',JSON.stringify(golden,null,2)));
    details('Component residuals · Full archive',table([['component','Component'],['unit','Unit'],['comparisons','Comparison'],['mismatches','Outside tolerance'],['difference','Maximum absolute residual']],
      replay.component_differences.map(r=>({...r,difference:r.maximum_absolute_difference.toExponential(5)}))));
    details('Combination classes and source coverage',table([['combination','Combination'],['label','Class'],['coverage','Matched / expected rows'],['sign_construction_scope','Candidate coverage'],['reason','Open issue']],
      s.classifications.map(r=>({...r,label:labels[r.classification] || r.classification,coverage:`${r.matched_rows} / ${2*r.expected_pairs}`}))));
    details('Method and outstanding acceptance checks',text('p','C is the signed static contribution. A is the coefficient-weighted spectral amplitude. '+
      'The method creates eight independent sign scenarios for P/M2/M3. Recorded 100%/30% factors and scaling apply once. '+
      'The CSI envelope model covers source arithmetic. TBDY §§4.4.2–4.4.4 and Annex 4B require separate verification.'),
      text('pre',JSON.stringify({blockers:p.blockers,direction_diagnostics:s.direction_diagnostics,references:s.references},null,2)));
    details('Source identifiers and calculation details for this page',text('pre',JSON.stringify({
      replay_result_sha256:replay.result_sha256,population_result_sha256:s.result_sha256,pmm_result_sha256:p.result_sha256,page},null,2)));
    for(const [title,url] of [['HTML report for this page','/report/column-bank?'],['JSON data for this page','/api/export-column-bank?']]) {
      const a=text('a',title);a.href=url+params;a.target='_blank';a.rel='noopener';el('columnExports').append(a);
    }
    const forensic=text('a','Complete VS26 sources and calculations · ZIP');
    forensic.href='/api/export-spectral-design?'+new URLSearchParams({run_id:report.run_id});forensic.target='_blank';forensic.rel='noopener';el('columnExports').append(forensic);
    total=page.total;
    el('columnPage').textContent=page.rows.length?`${offset+1}–${offset+page.rows.length} / ${total}`:'No records for this filter.';
    el('columnPrevious').disabled=offset===0;el('columnNext').disabled=offset+page.limit>=total;
  }
  async function load(resetFilters = false) {
    const ticket = ++epoch, selected = run.value;
    clearResult();
    if (resetFilters) {
      offset = 0; options(member, [], 'All columns'); options(loadCase, [], 'All outputs');
    }
    if (!selected) { el('columnStatus').textContent = 'No column archive selected.'; return; }
    const params = new URLSearchParams({run_id:selected, offset:String(offset)});
    const selectedView = view.value || 'native';
    const selectedProposal = proposal.value || '16Φ24';
    const selectedBeamDiameter = Number(beamProposal?.value || 20);
    el('columnProposalControl').hidden = !['overview','scwb-scenarios','spectral-design','spectral-candidates'].includes(selectedView);
    el('columnBeamProposalControl').hidden = !['beam-cages','scwb-scenarios'].includes(selectedView);
    const sectionView = ['reinforcement','stiffness','cages','transverse','joints','joint-ties','stiffness-scenarios','beam-cages'].includes(selectedView);
    loadCase.disabled = sectionView;
    if (member.value) params.set('member', member.value);
    if (loadCase.value && !sectionView) params.set('case', loadCase.value);
    if (selectedView !== 'native') params.set('view', selectedView);
    if(selectedView==='scwb-scenarios') {params.set('column_cage',selectedProposal);params.set('beam_diameter',String(selectedBeamDiameter));}
    if(['spectral-design','spectral-candidates'].includes(selectedView)) params.set('column_cage',selectedProposal);
    el('columnStatus').textContent = ['pmm','overview','pmm-quality','scwb','scwb-scenarios','spectral-design','spectral-candidates'].includes(selectedView) ? 'Preparing conditional column calculations…' : 'Verifying archive…';
    try {
      const report = await get('/api/column-bank?' + params);
      if (ticket !== epoch || selected !== run.value) return;
      if (report.run_id !== selected || report.formal_compliance !== 'NOT_PROVEN' || report.design_demand_authority !== 'DENIED') {
        throw new Error('Archive identity or coverage mismatch.');
      }
      if (resetFilters) {
        options(member, report.members.map(m => [m.frame_name,
          m.frame_name + ' · ' + (m.context?.frame?.story_label || 'Unresolved story')]), 'All columns');
        options(loadCase, report.case_coverage.map(c => [c.name, c.name + (c.row_count ? '' : ' · No data')]), 'All outputs');
      }
      el('columnStatus').textContent = selected + ' · NOT_PROVEN / NOT_READY';
      el('columnSummary').append(text('p', `${report.observed_column_count}/${report.selected_column_count} selected columns · ${report.force_row_count} force rows · ${report.recorded_output_count} recorded cases/combinations`));
      const trace=text('details','');trace.append(text('summary','Archive identity'),text('p', 'Source SHA-256: ' + report.source_archive_sha256, 'micro'));
      el('columnSummary').append(trace);
      if(selectedView==='spectral-envelopes') {renderSpectral(report,params);return;}
      if(['spectral-design','spectral-candidates'].includes(selectedView)) {renderSpectralDesign(report,params,selectedView,selectedProposal);return;}
      const chain = report.demand_chain;
      if (chain) {
        if (chain.source_run_id !== selected || chain.source_archive_sha256 !== report.source_archive_sha256 ||
            chain.design_demand_authority !== 'DENIED') throw new Error('Demand view belongs to a different source.');
        const d = chain.design_summary;
        el('columnDemandSummary').append(text('p', `${chain.combination_count} joints · ${chain.static_candidate_count} static source candidates · ` +
          `${d.row_count} design summary rows · ${d.unique_static_links} unique static source matches`));
        el('columnDemandSummary').append(text('p', 'These are analysis source records. Design combination, analysis order, and capacity approval remain open.', 'micro'));
        el('columnDemandRoutes').append(table([['combination','Combination'],['label','Class'],
          ['static_candidate_count','Static candidate'],['case_names','Source cases'],['reason','Open issue']],
          chain.combinations.map(r => ({...r,label:labels[r.classification] || r.classification}))));
        el('columnDemandRoutes').append(text('p', `${d.ambiguous_design_station_rows} duplicate station records · ` +
          `${d.references_without_exact_station} references without an exact station match. ` +
          'Blank ETABS PMM ratios remain blank. VMaj/VMin require an explicit mapping to V2/V3.', 'micro'));
        if (d.reason) el('columnDemandRoutes').append(text('p', d.reason, 'micro'));
      }
      const prechecks = report.column_prechecks;
      if (prechecks) {
        if (prechecks.source_run_id !== selected || prechecks.source_archive_sha256 !== report.source_archive_sha256 ||
            prechecks.source_demand_result_sha256 !== chain?.result_sha256 || prechecks.design_demand_authority !== 'DENIED') {
          throw new Error('Preliminary column calculation does not match the selected force chain.');
        }
        el('columnDemandSummary').append(text('p', `${prechecks.critical_selection.critical_state_count} critical static records · ` +
          `${prechecks.reinforcement_bounds.calculated_member_count} columns with longitudinal reinforcement area bounds`));
      }
      const stability = report.column_stability;
      if (stability && (stability.source_run_id !== selected || stability.source_archive_sha256 !== report.source_archive_sha256 ||
          stability.source_demand_result_sha256 !== chain?.result_sha256 || stability.source_prechecks_result_sha256 !== prechecks?.result_sha256 ||
          stability.design_demand_authority !== 'DENIED' || stability.actual_second_order_applied !== false)) {
        throw new Error('Stiffness calculation does not match the selected column source.');
      }
      const cages = report.column_cages, pmm = report.column_pmm;
      if (cages && (cages.source_run_id !== selected || cages.source_archive_sha256 !== report.source_archive_sha256 ||
          cages.source_demand_result_sha256 !== chain?.result_sha256 || cages.source_prechecks_result_sha256 !== prechecks?.result_sha256 ||
          cages.design_demand_authority !== 'DENIED' || cages.selected_design !== null)) {
        throw new Error('Reinforcement proposals do not match the selected column source.');
      }
      if (pmm && (pmm.schema !== 'tbdy.next.column-pmm-scenarios.v3' ||
          pmm.numerical_policy?.basis !== 'STRAIN_COMPATIBLE_POINT_AT_FIXED_N_AND_MOMENT_DIRECTION' ||
          pmm.numerical_policy?.solver_revision !== 'VS25_DIRECTION_ROOT' ||
          pmm.source_run_id !== selected || pmm.source_archive_sha256 !== report.source_archive_sha256 ||
          pmm.source_demand_result_sha256 !== chain?.result_sha256 || pmm.source_cages_result_sha256 !== cages?.result_sha256 ||
          pmm.source_stability_result_sha256 !== stability?.result_sha256 || pmm.design_demand_authority !== 'DENIED' ||
          pmm.pmm_population_reduced !== false || pmm.actual_second_order_applied !== false ||
          pmm.minimum_eccentricity_applied !== false || pmm.selected_design !== null || pmm.formal_compliance !== 'NOT_PROVEN')) {
        throw new Error('PMM calculation source or conditional scope mismatch.');
      }
      const transverse = report.column_transverse, shear = report.column_shear;
      if (transverse && (transverse.source_run_id !== selected || transverse.source_archive_sha256 !== report.source_archive_sha256 ||
          transverse.source_demand_result_sha256 !== chain?.result_sha256 || transverse.source_cages_result_sha256 !== cages?.result_sha256 ||
          transverse.design_demand_authority !== 'DENIED' || transverse.formal_compliance !== 'NOT_PROVEN' || transverse.selected_design !== null ||
          transverse.proposal_policy?.physical_arrangement_proven !== false)) {
        throw new Error('Transverse reinforcement proposal source or conditional scope mismatch.');
      }
      if (shear && (shear.source_run_id !== selected || shear.source_archive_sha256 !== report.source_archive_sha256 ||
          shear.source_demand_result_sha256 !== chain?.result_sha256 || shear.source_cages_result_sha256 !== cages?.result_sha256 ||
          shear.source_transverse_result_sha256 !== transverse?.result_sha256 || shear.design_demand_authority !== 'DENIED' ||
          shear.formal_compliance !== 'NOT_PROVEN' || shear.selected_design !== null || shear.ve_status !== 'NOT_PROVEN' ||
          shear.source_population_reduced !== false || shear.actual_second_order_applied !== false || shear.vc_zero_gate?.required !== null)) {
        throw new Error('Shear calculation source or conditional scope mismatch.');
      }
      const joints = report.column_joints;
      const kinematics = report.column_kinematics;
      const sensitivity = report.column_sensitivity;
      if (sensitivity && (sensitivity.source_run_id !== selected || sensitivity.source_archive_sha256 !== report.source_archive_sha256 ||
          sensitivity.source_bank_result_sha256 !== report.result_sha256 || sensitivity.source_demand_result_sha256 !== chain?.result_sha256 ||
          sensitivity.source_stability_result_sha256 !== stability?.result_sha256 ||
          sensitivity.source_kinematics_result_sha256 !== kinematics?.result_sha256 ||
          sensitivity.axis_convention !== 'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3' ||
          sensitivity.policy?.id !== 'TS500_EQ721_RM_0_0P5_1_REFERENCE_FAMILY' ||
          sensitivity.policy?.radius_basis !== 'TS500_RECTANGLE_0_30_BENDING_DIMENSION' ||
          sensitivity.policy?.actual_ei_interval_proven !== false || sensitivity.policy?.source_axial_force_is_design_nd !== false ||
          sensitivity.source_population_reduced !== false || sensitivity.actual_second_order_applied !== false ||
          sensitivity.actual_effective_length_lk_mm !== null || sensitivity.actual_beta !== null || sensitivity.actual_cm !== null ||
          sensitivity.actual_creep_ratio !== null || sensitivity.actual_sway_classification !== null ||
          sensitivity.magnified_design_moments !== null || sensitivity.approximate_method_applicability_proven !== false ||
          sensitivity.analysis_order !== 'NOT_PROVEN' || sensitivity.design_demand_authority !== 'DENIED' ||
          sensitivity.formal_compliance !== 'NOT_PROVEN' || sensitivity.engineering_release !== 'NOT_READY')) {
        throw new Error('Effective length sensitivity source or scenario mismatch.');
      }
      if (kinematics && (kinematics.source_run_id !== selected || kinematics.source_archive_sha256 !== report.source_archive_sha256 ||
          kinematics.source_bank_result_sha256 !== report.result_sha256 || kinematics.source_demand_result_sha256 !== chain?.result_sha256 ||
          kinematics.source_joints_result_sha256 !== joints?.result_sha256 ||
          kinematics.axis_convention !== 'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3' ||
          kinematics.coordinate_contract !== 'ETABS_POINT_OBJECT_UX_UY_UZ_RX_RY_RZ_GLOBAL' ||
          kinematics.analysis_order !== 'NOT_PROVEN' || kinematics.analysis_generation_qualified !== false ||
          kinematics.actual_second_order_applied !== false || kinematics.cm !== null || kinematics.beta !== null ||
          kinematics.magnified_design_moments !== null || kinematics.design_demand_authority !== 'DENIED' ||
          kinematics.formal_compliance !== 'NOT_PROVEN' || kinematics.engineering_release !== 'NOT_READY')) {
        throw new Error('Column end kinematics source or analysis scope mismatch.');
      }
      for (const calculation of [stability,cages,pmm,transverse,shear]) {
        if (calculation && calculation.axis_convention !== 'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3') {
          throw new Error('Section axis convention needs verification. Recalculate using the current convention.');
        }
      }
      if (joints && (joints.source_run_id !== selected || joints.source_archive_sha256 !== report.source_archive_sha256 ||
          joints.source_bank_result_sha256 !== report.result_sha256 || joints.source_demand_result_sha256 !== chain?.result_sha256 ||
          joints.source_cages_result_sha256 !== cages?.result_sha256 || joints.source_transverse_result_sha256 !== transverse?.result_sha256 ||
          joints.design_demand_authority !== 'DENIED' || joints.formal_compliance !== 'NOT_PROVEN' || joints.engineering_release !== 'NOT_READY' ||
          joints.ve_status !== 'NOT_PROVEN' || joints.scwb_status !== 'NOT_PROVEN' || joints.selected_design !== null ||
          joints.physical_geometry_proven !== false || joints.physical_joint_population_proven !== false ||
          joints.scenario !== 'CENTERLINE_AS_SECTION_CENTER_SCENARIO' ||
          joints.axis_convention !== 'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3')) {
        throw new Error('Joint calculation source or conditional scope mismatch.');
      }
      for (const [label, url] of [
        ['HTML calculation report', '/report/column-bank?'],
        ['Tam JSON', '/api/export-column-bank?format=json&'],
        ['SQLite force bank', '/api/export-column-bank?format=sqlite&']]) {
        const link = text('a', label); link.href = url + 'run_id=' + encodeURIComponent(selected);
        link.target = '_blank'; link.rel = 'noopener'; el('columnExports').append(link);
      }
      const chosen = report.members.find(m => m.frame_name === member.value);
      if (chosen && selectedView !== 'overview') {
        const ctx = chosen.context || {}, g = chosen.station_geometry || {};
        el('columnContext').append(text('p', `${ctx.frame?.section_assigned || 'Unresolved section'} · ` +
          `b2/b3: ${show(ctx.geometry?.T2_cm)}/${show(ctx.geometry?.T3_cm)} cm · Fc/Fy: ${show(ctx.material?.fc_MPa)}/${show(ctx.material?.fy_MPa)} MPa · ` +
          `I–J: ${show(g.object_i_j_length_m)} m · J offset: ${show(g.offset_j_m)} m · last output is at joint J: ${show(g.last_station_is_joint_j)}`));
        el('columnContext').append(text('p', 'TS500 clear and effective lengths require separate evidence. Model settings are recorded as reinforcement inputs.', 'micro'));
        if (chosen.reason_codes.length) el('columnContext').append(text('p', chosen.reason_codes.join(' · '), 'warn'));
      }
      const page = selectedView === 'native' ? report.force_page : report.demand_page;
      if ((selectedView === 'critical' || selectedView === 'reinforcement') && !prechecks) throw new Error('No preliminary column calculation.');
      if ((selectedView === 'stiffness' || selectedView === 'eccentricity') && !stability) throw new Error('No stiffness and eccentricity calculation.');
      if (selectedView === 'cages' && !cages) throw new Error('No reinforcement proposal.');
      if (selectedView === 'pmm' && !pmm) throw new Error('No conditional PMM calculation.');
      if (selectedView === 'transverse' && !transverse) throw new Error('No transverse reinforcement proposal.');
      if (selectedView === 'shear' && !shear) throw new Error('No conditional shear calculation.');
      if (['joints','joint-ties'].includes(selectedView) && !joints) throw new Error('No joint references.');
      if (['end-forces','kinematics'].includes(selectedView) && !kinematics) throw new Error('No column end source link.');
      if (['stiffness-scenarios','length-sensitivity'].includes(selectedView) && !sensitivity) throw new Error('No effective length sensitivity results.');
      const overview = report.column_overview;
      const quality = report.column_pmm_quality;
      const scwb = report.column_scwb;
      const beams = report.beam_end_references;
      const scenarios = report.scwb_scenarios;
      if(selectedView==='scwb-scenarios' && (!scenarios || scenarios.schema!=='tbdy.next.scwb-proposal-scenarios.v1' ||
          scenarios.policy!=='COMPLETE_JOINT_SAME_COLUMN_CASE_EXPLICIT_BEAM_N0_SIGNED_PROPOSALS_V1' ||
          scenarios.axis_convention!=='CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3' ||
          scenarios.source_run_id!==selected || scenarios.source_archive_sha256!==report.source_archive_sha256 ||
          scenarios.source_demand_result_sha256!==chain?.result_sha256 || scenarios.source_joints_result_sha256!==joints?.result_sha256 ||
          scenarios.source_scwb_result_sha256!==scwb?.result_sha256 || scenarios.source_beam_result_sha256!==beams?.result_sha256 ||
          scenarios.member_id_filter!==(member.value || null) || scenarios.output_case_filter!==(loadCase.value || null) ||
          scenarios.display_column_label!==selectedProposal || scenarios.display_beam_diameter_mm!==selectedBeamDiameter ||
          scenarios.neighbouring_participants_retained!==true || scenarios.source_population_reduced!==false ||
          scenarios.automatic_scenario_selection!==false || scenarios.selected_design!==null || scenarios.actual_or_selected_cages_bound!==false ||
          scenarios.physical_joint_population_proven!==false || scenarios.physical_joint_moment_transfer_proven!==false ||
          scenarios.normative_exception_applied!==false || scenarios.earthquake_compatible_minimum_proven!==false ||
          scenarios.actual_second_order_applied!==false || scenarios.scwb_ratio_count!==0 || scenarios.factor!==1.2 ||
          scenarios.rotation_basis!=='RIGHT_HAND_ABOUT_GLOBAL_Z_CROSS_DIRECTION' ||
          scenarios.case_basis!=='COLUMN_STATIC_SOURCE_N_ONLY_BEAM_N0_PROPOSALS_INDEPENDENT_OF_CASE' ||
          scenarios.ratio_definition!=='SUM_MRC_PROPOSAL_AT_COLUMN_SOURCE_N_OVER_1_2_SUM_MRB_PROPOSAL_AT_N0' ||
          scenarios.formal_compliance!=='NOT_PROVEN' || scenarios.design_demand_authority!=='DENIED' || scenarios.engineering_release!=='NOT_READY' ||
          scenarios.filtered_summary_count!==page?.total || !['NATIVE_JOINT_GRAPH_BOUND','BLOCKED_NATIVE_JOINT_GRAPH'].includes(scenarios.source_population_status) ||
          (scenarios.source_population_status==='NATIVE_JOINT_GRAPH_BOUND' && (scenarios.case_count!==scenarios.expected_case_count ||
            scenarios.summary_count!==scenarios.expected_summary_count || scenarios.filtered_summary_count!==2*scenarios.filtered_joint_node_count)) ||
          (scenarios.source_population_status==='BLOCKED_NATIVE_JOINT_GRAPH' && (scenarios.joint_node_count!==null || scenarios.expected_case_count!==null)))) {
        throw new Error('SCWB proposal source or scope mismatch.');
      }
      if(selectedView==='beam-cages' && (!beams || beams.schema!=='tbdy.next.beam-end-capacity-scenarios.v1' ||
          beams.axis_convention!=='CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3' ||
          beams.policy?.id!=='VS23_SINGLE_ROW_PHI16_20_24_SOURCE_AREA_TARGET_N0_V1' ||
          beams.policy.cover_basis!=='CSI_FACE_TO_LONGITUDINAL_GROUP_CENTROID' ||
          beams.policy.axial_force_scenario_n!==0 || beams.policy.source_beam_axial_force_applied!==false ||
          beams.policy.automatic_design_selection!==false || beams.policy.physical_cage_proven!==false ||
          JSON.stringify(beams.policy.diameters_mm)!=='[16,20,24]' || ![16,20,24].includes(selectedBeamDiameter) ||
          beams.source_run_id!==selected || beams.source_archive_sha256!==report.source_archive_sha256 ||
          beams.source_demand_result_sha256!==chain?.result_sha256 || beams.source_joints_result_sha256!==joints?.result_sha256 ||
          beams.member_id_filter!==(member.value || null) || beams.source_population_reduced!==false ||
          beams.selected_design!==null || beams.actual_or_selected_beam_capacity_bound!==false || beams.scwb_ratio!==null ||
          beams.design_demand_authority!=='DENIED' || beams.formal_compliance!=='NOT_PROVEN' || beams.engineering_release!=='NOT_READY' ||
          beams.filtered_end_count!==page?.total || !['NATIVE_JOINT_GRAPH_BOUND','BLOCKED_NATIVE_JOINT_GRAPH'].includes(beams.source_population_status) ||
          (beams.source_population_status==='NATIVE_JOINT_GRAPH_BOUND' && (beams.source_end_count!==beams.expected_end_count ||
            beams.expected_end_count!==2*beams.target_beam_count || beams.expected_candidate_count!==3*beams.expected_end_count)) ||
          (beams.source_population_status==='BLOCKED_NATIVE_JOINT_GRAPH' && (beams.expected_end_count!==null || beams.target_beam_count!==null)))) {
        throw new Error('Beam-end calculation source or scope mismatch.');
      }
      if (selectedView === 'scwb' && (!scwb || scwb.schema !== 'tbdy.next.scwb-source-references.v1' ||
          scwb.policy !== 'COMPLETE_JOINT_ROSTER_SAME_STATIC_CASE_COLUMN_AXIS_REFERENCE_V1' ||
          scwb.axis_convention !== 'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3' ||
          scwb.source_run_id !== selected || scwb.source_archive_sha256 !== report.source_archive_sha256 ||
          scwb.source_demand_result_sha256 !== chain?.result_sha256 || scwb.source_cages_result_sha256 !== cages?.result_sha256 ||
          scwb.source_joints_result_sha256 !== joints?.result_sha256 || scwb.source_kinematics_result_sha256 !== kinematics?.result_sha256 ||
          scwb.member_id_filter !== (member.value || null) || scwb.output_case_filter !== (loadCase.value || null) ||
          scwb.source_population_reduced !== false || scwb.neighbouring_participants_retained !== true ||
          scwb.required_beam_steel_used_as_capacity !== false || scwb.approximate_as_half_fallback_used !== false ||
          scwb.earthquake_compatible_minimum_proven !== false || scwb.normative_exception_applied !== false ||
          scwb.physical_joint_population_proven !== false || scwb.scwb_ratio_count !== 0 ||
          scwb.actual_second_order_applied !== false || scwb.selected_design !== null ||
          scwb.design_demand_authority !== 'DENIED' || scwb.formal_compliance !== 'NOT_PROVEN' || scwb.engineering_release !== 'NOT_READY' ||
          !['NATIVE_JOINT_GRAPH_BOUND','BLOCKED_NATIVE_JOINT_GRAPH'].includes(scwb.source_population_status) ||
          scwb.expected_column_end_count !== 2*scwb.selected_column_count || scwb.summaries.length !== page?.total ||
          (scwb.source_population_status === 'NATIVE_JOINT_GRAPH_BOUND' &&
            (scwb.graph_status !== 'NATIVE_ENDPOINT_GRAPH_BOUND' || scwb.joint_case_count !== scwb.expected_joint_case_count ||
             scwb.column_end_count !== scwb.expected_column_end_count || scwb.column_reference_count !== scwb.expected_column_reference_count ||
             scwb.filtered_joint_case_count !== scwb.filtered_joint_node_count*scwb.static_cases.length*12)) ||
          (scwb.source_population_status === 'BLOCKED_NATIVE_JOINT_GRAPH' &&
            (scwb.graph_status !== 'BLOCKED_INPUTS' || scwb.joint_node_count !== null || scwb.expected_joint_case_count !== null ||
             scwb.joint_case_count !== 0 || scwb.column_reference_count !== 0)))) {
        throw new Error('SCWB calculation source or scope mismatch.');
      }
      if (selectedView === 'pmm-quality' && (!quality || quality.schema !== 'tbdy.next.column-pmm-numerical-reference.v2' ||
          quality.policy_id !== 'CRITICAL_PMM_STRIP_GAUSS_BISECTION_WITH_PRIMARY_DIRECTION_ROOT_V2' ||
          quality.primary_capacity_basis !== 'STRAIN_COMPATIBLE_POINT_AT_FIXED_N_AND_MOMENT_DIRECTION' ||
          quality.primary_solver_revision !== 'VS25_DIRECTION_ROOT' ||
          quality.numerical_policy?.primary_direction_absolute_tolerance_nmm !== 1000 ||
          quality.axis_convention !== 'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3' ||
          quality.source_run_id !== selected || quality.source_archive_sha256 !== report.source_archive_sha256 ||
          quality.source_demand_result_sha256 !== chain?.result_sha256 || quality.source_cages_result_sha256 !== cages?.result_sha256 ||
          quality.source_pmm_result_sha256 !== pmm?.result_sha256 ||
          quality.member_id_filter !== (member.value || null) || quality.output_case_filter !== (loadCase.value || null) ||
          quality.critical_subset_only !== true || quality.critical_selection_independently_verified !== false ||
          quality.full_primary_population_independently_checked !== false || quality.primary_results_changed !== false ||
          quality.same_declared_material_model !== true || quality.independent_material_model_validation !== false ||
          quality.continuous_error_bound_proven !== false || quality.global_root_uniqueness_proven !== false ||
          quality.actual_second_order_applied !== false || quality.selected_design !== null ||
          quality.design_demand_authority !== 'DENIED' || quality.formal_compliance !== 'NOT_PROVEN' || quality.engineering_release !== 'NOT_READY' ||
          quality.comparison_count !== quality.critical_target_count || quality.comparison_count !== page?.total ||
          quality.numerical_policy?.comparison_relative_tolerance !== .002 || quality.numerical_policy?.primary_level_spread_added_to_budget !== false)) {
        throw new Error('Independent PMM comparison source or scope mismatch.');
      }
      if (selectedView === 'overview' && (!overview || overview.schema !== 'tbdy.next.column-overview.v1' ||
          overview.policy !== 'EXPLICIT_CAGE_DISPLAY_ONLY_SAME_SOURCE_VECTOR_V1' ||
          overview.axis_convention !== 'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3' ||
          overview.source_run_id !== selected || overview.source_archive_sha256 !== report.source_archive_sha256 ||
          overview.source_demand_result_sha256 !== chain?.result_sha256 || overview.source_cages_result_sha256 !== cages?.result_sha256 ||
          overview.source_pmm_result_sha256 !== pmm?.result_sha256 || overview.source_shear_result_sha256 !== shear?.result_sha256 ||
          overview.source_sensitivity_result_sha256 !== sensitivity?.result_sha256 ||
          overview.member_id_filter !== (member.value || null) || overview.output_case_filter !== (loadCase.value || null) ||
          overview.automatic_design_selection !== false || overview.selected_design !== null ||
          overview.underlying_source_population_reduced !== false || overview.actual_second_order_applied !== false ||
          overview.spectral_design_vectors_formed !== false || overview.design_demand_authority !== 'DENIED' ||
          overview.formal_compliance !== 'NOT_PROVEN' || overview.engineering_release !== 'NOT_READY' ||
          !overview.candidate_labels.includes(selectedProposal))) throw new Error('Column overview source or scope mismatch.');
      if (!page || (selectedView !== 'native' && page.view !== selectedView)) throw new Error('The requested demand view is unavailable.');
      total = page.total; offset = page.offset;
      const identity = [['Obj','Column'], ['Elm','Analysis element'], ['ObjSta','Object station'], ['ElmSta','Element station'],
        ['LoadCase','Case / combination'], ['StepType','Step'], ['StepNum','No']];
      if (selectedView === 'overview') {
        renderOverview(report,page,selectedProposal);
      } else if (selectedView === 'pmm-quality') {
        renderQuality(quality,page);
      } else if (selectedView === 'scwb') {
        renderScwb(scwb,page);
      } else if (selectedView === 'beam-cages') {
        renderBeams(beams,page,selectedBeamDiameter);
      } else if (selectedView === 'scwb-scenarios') {
        renderScenarios(scenarios,page);
      } else if (selectedView === 'native') {
        el('columnUnits').textContent = 'Native signs are preserved. Force is in kN, moment in kN·m, and stations in m.';
        el('columnForces').append(table([...identity,...['P','V2','V3','T','M2','M3'].map(c => [c,c])], page.rows));
      } else if (selectedView === 'static' || selectedView === 'critical') {
        el('columnUnits').textContent = 'N=−P, positive in compression and negative in tension. Force is in kN, moment in kN·cm, and stations in m. Moments use CSI local axes 2–3. Analysis order is unverified.';
        const reason = selectedView === 'critical' ? [['criticalReason','Governing criterion']] : [];
        if (selectedView === 'critical') {
          if (!report.critical_scope || report.critical_scope.pmm_population_reduced !== false) throw new Error('Governing selection coverage could not be verified.');
          el('columnContext').append(text('p', `${report.critical_scope.candidate_count} filtered static candidates considered for the critical set. ` +
            'All ties and the complete PMM candidate population are retained. Each component maximum stays linked to its own vector.', 'micro'));
        }
        el('columnForces').append(table([...reason,...identity,['N_compression_kN','N (compression +)'], ['V2_kN','V2'],
          ['V3_kN','V3'],['T_kNcm','T'],['M2_kNcm','M2'],['M3_kNcm','M3']],
          page.rows.map(r => ({...r.native_key,...r.domain_values,criticalReason:(r.criteria || []).map(c => labels[c] || c).join(', ')}))));
      } else if (selectedView === 'reinforcement') {
        el('columnUnits').textContent = 'TBDY 2018 §7.3.2.1 gives As,min = 1% Ac and As,max = 4% Ac. Areas are in cm². Ductility class, actual reinforcement, bar sizes/counts, and splices require separate verification.';
        el('columnForces').append(table([['member_id','Column'],['story','Story'],['section_name','Section'],
          ['gross_area_cm2','Ac'],['minimum_as_cm2','As,min'],['maximum_as_cm2','As,max'],['provided_as_cm2','Verified actual As'],
          ['sourceMatches','Matches source AsMin'],['sourceAbove','Above reference'],['sourceBelow','Below reference'],
          ['sourceUnknown','Unresolved AsMin'],['label','Calculation'],['reason','Open issue']], page.rows.map(r => ({...r,label:labels[r.status] || r.status,
            sourceMatches:r.asmin_source_counts.NUMERICAL_MATCH || 0,sourceAbove:r.asmin_source_counts.SOURCE_ABOVE_REFERENCE || 0,
            sourceBelow:r.asmin_source_counts.SOURCE_BELOW_REFERENCE || 0,
            sourceUnknown:Object.keys(r.asmin_source_counts).length ? (r.asmin_source_counts.NOT_PROVEN || 0) : 'No records'}))));
      } else if (selectedView === 'stiffness') {
        const fmt = v => v == null ? null : Number(v.toPrecision(10));
        el('columnUnits').textContent = 'Gross properties use I in cm⁴, r in mm, E in MPa, and lengths in m. Effective EI and the TS500 clear and effective lengths require separate evidence.';
        el('columnContext').append(text('p', `${stability.calculated_section_count} columns · ${stability.distinct_section_count} distinct sections · ` +
          `${stability.native_property_match_count} matching source properties. ` +
          'Second-order analysis requires clear length, k, sway classification, creep, and analysis basis. The table gives both r=√(I/A) and the 0.30h approximation.', 'micro'));
        el('columnForces').append(table([['member_id','Column'],['story','Story'],['section_name','Section'],
          ['i22','I22'],['i33','I33'],['r22','r22'],['r33','r33'],['e','E'],['object','I–J boyu'],
          ['span','Output span'],['comparison','Section source comparison']], page.rows.map(r=>({...r,
            i22:fmt(r.section ? r.section.i22_mm4/1e4 : null),i33:fmt(r.section ? r.section.i33_mm4/1e4 : null),
            r22:fmt(r.section?.r22_exact_mm),r33:fmt(r.section?.r33_exact_mm),e:fmt(r.elastic?.observed_E_MPa),
            object:r.lengths.object_i_j_m,span:r.lengths.output_face_span_m,comparison:labels[r.property_comparison_status] || r.property_comparison_status}))));
      } else if (selectedView === 'eccentricity') {
        el('columnUnits').textContent = 'TS500 6.16 gives e,min = 15 + 0.03h (mm). The N·e,min reference is in kN·cm. End-moment applicability and the required forces remain subject to verification.';
        el('columnContext').append(text('p', 'Native T3 follows local 2 and T2 follows local 3. Use h=T2 for M2 and h=T3 for M3. The reference applies to compression. Design ends and combinations require separate verification.', 'micro'));
        el('columnForces').append(table([['Obj','Column'],['Elm','Analysis element'],['ObjSta','Station (m)'],['LoadCase','Combination'],
          ['n','N (kN)'],['m2','|M2|'],['ref2','M2 reference'],['s2','M2 comparison'],['m3','|M3|'],['ref3','M3 reference'],['s3','M3 comparison']],
          page.rows.map(r=>({...r.native_key,n:r.axes[0].n_compression_kn,m2:r.axes[0].source_abs_moment_kNcm,
            ref2:r.axes[0].reference_minimum_moment_kNcm,s2:labels[r.axes[0].status] || r.axes[0].status,
            m3:r.axes[1].source_abs_moment_kNcm,ref3:r.axes[1].reference_minimum_moment_kNcm,
            s3:labels[r.axes[1].status] || r.axes[1].status}))));
      } else if (selectedView === 'cages') {
        el('columnUnits').textContent = 'Three proposals use 16Φ24, 16Φ28, or 16Φ32 with Φ12 stirrups. Model cover is to the outer stirrup face. The layouts are proposals.';
        el('columnContext').append(text('p','Aggregate, stirrups, crossties, splices, and material factors require project approval. Local 2 points right and local 3 points up.', 'micro'));
        if (member.value) for (const row of page.rows.filter(r=>r.geometry_status==='PROPOSED_GEOMETRY_CALCULATED')) {
          el('columnContext').append(cageDrawing(row));
        }
        el('columnForces').append(table([['member_id','Column'],['story','Story'],['label','Proposal'],['as','As (cm²)'],
          ['rho','ρ (%)'],['center_offset_mm','Cover to bar center (mm)'],['minimum_clear_spacing_mm','Clear spacing (mm)'],
          ['area','Area comparison'],['geometry','Geometry'],['reason','Open issue']],page.rows.map(r=>({...r,
            as:rounded(r.as_cm2),rho:rounded(r.rho_percent),area:labels[r.area_ratio_status] || r.area_ratio_status,
            geometry:labels[r.geometry_status] || r.geometry_status}))));
      } else if (selectedView === 'pmm') {
        el('columnUnits').textContent = 'Each unmodified static source vector is evaluated against the proposed cage. M2/M3 and radial capacities are in kN·m. The ratio is dimensionless. Scenario factors are γc=1.5 and γs=1.15. Minimum eccentricity and second-order effects are pending.';
        el('columnContext').append(text('p',`${pmm.static_state_count} static states × 3 proposals = ${pmm.assessment_count} comparisons across the archive. `+
          'Each ratio covers its resolved scenario. Seismic design population coverage and final reinforcement require separate verification.', 'micro'));
        el('columnContext').append(text('p','Capacity is the strain-compatible point at fixed N in the source moment direction. '+
          'See Independent PMM numerical comparison for the critical equilibrium residuals.','micro'));
        el('columnForces').append(table([['Obj','Column'],['ObjSta','Station (m)'],['Elm','Element'],['LoadCase','Combination'],
          ['candidate_label','Proposal'],['n','N (kN)'],['m2','M2'],['m3','M3'],['capacity','Radial capacity'],
          ['ratio','Conditional ratio'],['label','Numerical status'],['reasonLabel','Open issue']],page.rows.map(r=>({...r.native_key,...r,
            n:rounded(r.domain_values.N_compression_kN),m2:rounded(r.native_values.M2),m3:rounded(r.native_values.M3),
            capacity:rounded(r.radial_capacity_kNm),ratio:rounded(r.utilization),label:labels[r.status] || r.status,
            reasonLabel:labels[r.reason] || r.reason}))));
      } else if (selectedView === 'transverse') {
        el('columnUnits').textContent = 'The Φ12/100 proposal uses one outer stirrup and three crossties in each direction. Ash and Asw are in mm² and dimensions in mm. Ack uses outside dimensions, and bk uses stirrup centerlines. High-ductility applicability is pending.';
        el('columnContext').append(text('p','Confinement areas are shown for both axial-load branches. Branch selection, clear length, actual confinement zone, hook anchorage, and three-dimensional detailing require verification.','micro'));
        const drawn = new Set();
        if (member.value) for (const row of page.rows) {
          const cage = cages?.candidates?.find(c=>c.candidate_id===row.candidate_id);
          if (cage && row.layout && !drawn.has(row.candidate_id)) {
            el('columnContext').append(cageDrawing(cage,row.layout)); drawn.add(row.candidate_id);
          }
        }
        el('columnForces').append(table([['member_id','Column'],['candidate_label','Longitudinal proposal'],['shear_axis','Shear direction'],
          ['bkAxis','bk axis'],['bk','bk'],['ash','Proposed Ash'],['reqHigh','Ash · High N'],['reqLow','Ash · Low N'],
          ['gap','Horizontal stirrup-leg spacing'],['smax','Confinement spacing limit s'],['label','Calculation'],['reason','Open issue']],page.rows.map(r=>({...r,
            bkAxis:r.direction?.bk_axis,bk:rounded(r.direction?.bk_mm),ash:rounded(r.direction?.ash_mm2),
            reqHigh:rounded(r.direction?.confinement.high_axial_required_ash_mm2),
            reqLow:rounded(r.direction?.confinement.low_axial_required_ash_mm2),gap:rounded(r.direction?.maximum_lateral_leg_spacing_mm),
            smax:rounded(r.confinement_spacing_max_mm),label:labels[r.status] || r.status}))));
      } else if (selectedView === 'shear') {
        el('columnUnits').textContent = 'Forces are in kN. For V2, bw=T2 and d=T3−cover to center. For V3, bw=T3 and d=T2−cover to center. Vr=Vc+Vw and the ratio is |source V|/Vr. Design Ve remains unverified.';
        el('columnContext').append(text('p',`${shear.static_state_count} static states × 3 proposals × 2 directions = ${shear.assessment_count} comparisons across the archive. `+
          'Both concrete contribution scenarios are shown. The seismic Vc=0 condition, torsion interaction, capacity shear, and final reinforcement remain open.','micro'));
        el('columnForces').append(table([['Obj','Column'],['ObjSta','Station (m)'],['LoadCase','Combination'],
          ['candidate_label','Longitudinal proposal'],['shear_axis','Direction'],['v','Signed V'],['vc','Vc · TS500'],['vw','Vw'],
          ['vr','Vr · TS500'],['ratio','|V|/Vr · TS500'],['ratioZero','|V|/Vr · Vc=0'],['label','Calculation'],['reasonLabel','Open issue']],
          page.rows.map(r=>({...r.native_key,...r,v:rounded(r.calculation?.source_signed_v_kn),
            vc:rounded(r.calculation?.branches.ts500.vc_kn),vw:rounded(r.calculation?.branches.zero_concrete.vw_kn),
            vr:rounded(r.calculation?.branches.ts500.vr_kn),ratio:rounded(r.calculation?.branches.ts500.source_utilization),
            ratioZero:rounded(r.calculation?.branches.zero_concrete.source_utilization),label:labels[r.status] || r.status,
            reasonLabel:labels[r.reason] || r.reason}))));
      } else if (selectedView === 'stiffness-scenarios' || selectedView === 'length-sensitivity') {
        el('columnContext').append(text('p','Rm = 0, 0.5, and 1 are scenario inputs. Project creep and effective EI require verification. ' +
          'The radius approximation is i=0.30h. The 22i reference applies conditionally to sway, 40i is an upper limit for non-sway, and 100i is the approximate method limit.','micro'));
        if (selectedView === 'stiffness-scenarios') {
          el('columnUnits').textContent = 'TS500 7.19 / 7.21 uses EI=0.4EcIc/(1+Rm) and Nk(kN)=π²EI/(1000lk²). In the formulas, lk is in mm, Ec in MPa, Ic in mm⁴, and EI in N·mm². Table lengths are in m. Project lk, k, and clear length remain open.';
          const scientific = v => typeof v === 'number' ? v.toExponential(4) : null;
          el('columnForces').append(table([['member_id','Column'],['axis','Axis'],['ec_mpa_observed','Ec (MPa)'],
            ['inertia','Ic (mm⁴)'],['radius','i: 0.30h / √(I/A) (mm)'],['ei','EI: Rm 0 / 0.5 / 1 (N·mm²)'],
            ['lengths','22i / 40i / 100i (m)'],['label','Scope'],['reason','Open issue']],page.rows.map(r=>({...r,
              inertia:scientific(r.gross_inertia_mm4),radius:[rounded(r.radius_reference_mm),rounded(r.radius_exact_mm)],
              ei:r.scenarios.map(s=>scientific(s.effective_ei_nmm2_scenario)),
              lengths:[r.length_22i_mm,r.length_40i_mm,r.length_100i_mm].map(v=>v==null ? null : rounded(v/1000)),
              label:labels[r.status] || r.status}))));
          if (member.value) {
            const details=text('details','');details.append(text('summary','Euler loads at reference lengths'));
            details.append(table([['axis','Axis'],['rm','Rm scenario'],['n22','Nk: 22i (kN)'],['n40','Nk: 40i (kN)'],['n100','Nk: 100i (kN)']],
              page.rows.flatMap(r=>r.scenarios.map(s=>({axis:r.axis,rm:s.creep_ratio_scenario,
                n22:rounded(s.length_references[0].nk_kn_scenario),n40:rounded(s.length_references[1].nk_kn_scenario),
                n100:rounded(s.length_references[2].nk_kn_scenario)})))));
            el('columnContext').append(details);
          }
        } else {
          el('columnUnits').textContent = 'lk,0(mm)=π√[EI/(1.3×1000×Nsource(kN))]. EI is in N·mm². The table shows the length in m at which the Eq. (7.24) denominator vanishes. Every static station and both axes are retained. The calculation applies to compression.';
          el('columnContext').append(text('p',`${sensitivity.static_state_count} static records · ${sensitivity.zero_length_reference_count} zero-denominator lengths. `+
            'The approximate method ends at 100i. Cm, β, and design moments require verified inputs.','micro'));
          el('columnForces').append(table([['member_id','Column'],['case','Combination'],['station','Station (m)'],['axis','Axis'],
            ['n_source_compression_kn','Source N (kN, compression +)'],['lengths','lk,0: Rm 0 / 0.5 / 1 (m)'],
            ['beyond','Beyond 100i: 0 / 0.5 / 1'],['label','Calculation'],['reason','Open issue']],page.rows.map(r=>({...r,
              case:r.native_key.LoadCase,station:r.native_key.ObjSta,
              lengths:r.scenarios.map(s=>s.zero_denominator_length_mm==null ? '—' : rounded(s.zero_denominator_length_mm/1000)),
              beyond:r.scenarios.map(s=>s.zero_length_exceeds_100i_reference==null ? '—' : s.zero_length_exceeds_100i_reference ? 'Yes' : 'No'),
              label:labels[r.status] || r.status}))));
          if (member.value) {
            const detail=text('details','');detail.append(text('summary','Recorded axial force variation and method requirements'));
            detail.append(table([['output_case','Combination'],['recorded_static_station_count','Station'],['n_i_kn','I kesiti N (kN)'],
              ['n_j_kn','J kesiti N (kN)'],['end_n_j_minus_i_kn','NJ−NI (kN)'],['recorded_range_kn','N range across recorded stations (kN)'],
              ['label','Source']],(sensitivity.axial_profiles || []).map(r=>({...r,label:labels[r.recorded_values_status] || r.recorded_values_status}))));
            detail.append(text('p','The approximate method requires constant section and axial force, linear elastic analysis, and the minimum eccentricity basis. Verify these inputs for the complete member.','micro'));
            el('columnContext').append(detail);
            const denominator=text('details','');denominator.append(text('summary','Denominator 1−1.3Nsource/Nk at reference lengths'));
            denominator.append(table([['case','Combination'],['station','Station'],['axis','Axis'],['rm','Rm'],['lambda','lk/i reference'],
              ['lk','lk (m)'],['nk','Nk (kN)'],['value','Denominator'],['label','Numerical scope']],page.rows.flatMap(r=>r.scenarios.flatMap(s=>
                s.at_reference_lengths.map(v=>({case:r.native_key.LoadCase,station:r.native_key.ObjSta,axis:r.axis,rm:s.creep_ratio_scenario,
                  lambda:v.lk_over_i_reference,lk:rounded(v.effective_length_lk_mm_scenario/1000),nk:rounded(v.nk_kn_scenario),
                  value:rounded(v.source_denominator),label:labels[v.status] || v.status}))))));
            el('columnContext').append(denominator);
          }
        }
      } else if (selectedView === 'end-forces' || selectedView === 'kinematics') {
        el('columnContext').append(text('p',`${kinematics.linked_member_case_count}/${kinematics.expected_member_case_count} column–combination source links. `+
          'Analysis order, Cm, β, and magnified moments require verification.','micro'));
        const details = text('details',''); details.append(text('summary','Analysis stiffness source'));
        const names = kinematics.analysis_basis.combinations.find(c=>c.combination===loadCase.value)?.case_names;
        details.append(table([['case_name','Case'],['stiffness_type','Stiffness setting'],['nonlinear_case_raw','Initial case record'],
          ['label','Source status'],['reason','Open issue']],kinematics.analysis_basis.cases.filter(c=>!names || names.includes(c.case_name))
          .map(c=>({...c,label:labels[c.status] || c.status}))));
        details.append(text('p','A linear static case can reference different stiffness settings. A recorded “None” leaves the initial condition unverified.','micro'));
        el('columnContext').append(details);
        if (selectedView === 'end-forces') {
          el('columnUnits').textContent = 'Each row pairs two source cuts in one single-valued static combination. P is positive in tension. Forces are in kN, moments in kN·m, and stations in m. Joint and support faces require physical verification. Interior stations are retained.';
          const values = (pair,end,keys) => pair?.[end] ? keys.map(k=>rounded(pair[end].native_values[k])) : null;
          el('columnForces').append(table([['member_id','Column'],['output_case','Combination'],['iCut','I: element / station'],
            ['jCut','J: element / station'],['iF','I: P / V2 / V3'],['iM','I: T / M2 / M3'],
            ['jF','J: P / V2 / V3'],['jM','J: T / M2 / M3'],['label','Source link'],['reason','Open issue']],page.rows.map(r=>({...r,
              iCut:r.force_pair ? [r.force_pair.i.native_key.Elm,r.force_pair.i.native_key.ObjSta] : null,
              jCut:r.force_pair ? [r.force_pair.j.native_key.Elm,r.force_pair.j.native_key.ObjSta] : null,
              iF:values(r.force_pair,'i',['P','V2','V3']),iM:values(r.force_pair,'i',['T','M2','M3']),
              jF:values(r.force_pair,'j',['P','V2','V3']),jM:values(r.force_pair,'j',['T','M2','M3']),
              label:labels[r.status] || r.status,reason:r.force_reason || r.kinematics_reason}))));
        } else {
          el('columnUnits').textContent = 'Global joint U/R values are transformed to column local axes 1–2–3. Δu is in mm, joint length L in m, and α2=−Δu3/L, α3=Δu2/L, and R−α are in radians. These quantities describe joint kinematics.';
          el('columnForces').append(table([['member_id','Column'],['output_case','Combination'],['points','I / J joint'],
            ['length','L (m)'],['delta','Δu1 / Δu2 / Δu3 (mm)'],['alpha','α2 / α3 (rad)'],
            ['ri','I: R2−α2 / R3−α3'],['rj','J: R2−α2 / R3−α3'],['label','Source link'],['reason','Open issue']],page.rows.map(r=>{
              const c=r.calculation; return {...r,points:[r.point_i,r.point_j],length:c?.object_i_j_length_m,
                delta:c?.delta_local_m.map(v=>rounded(v*1000)),alpha:c ? [rounded(c.chord_alpha2_rad),rounded(c.chord_alpha3_rad)] : null,
                ri:c ? [rounded(c.joint_i_relative_r2_rad),rounded(c.joint_i_relative_r3_rad)] : null,
                rj:c ? [rounded(c.joint_j_relative_r2_rad),rounded(c.joint_j_relative_r3_rad)] : null,
                label:labels[r.status] || r.status,reason:r.kinematics_reason || r.force_reason};})));
          el('columnContext').append(text('p','Printed zeros reflect source precision. Releases and offsets require a separate section-end rotation evaluation.','micro'));
        }
      } else if (selectedView === 'joints') {
        el('columnUnits').textContent = 'TBDY 7.5 centered orthogonal scenario. The confined classification requires beams on four faces with each width ≥75%. Shear limits are in kN. Ve and SCWB remain open.';
        el('columnContext').append(text('p',`${joints.joint_node_count} joints · ${joints.column_end_count} column ends · ${joints.geometric_limit_count} directional limits. `+
          'Each row uses the section of its end column. Joint faces and eccentricity require physical verification.','micro'));
        if (joints.graph.reason) el('columnContext').append(text('p',joints.graph.reason,'warn'));
        el('columnForces').append(table([['member_id','Column'],['end','End'],['point_id','Joint'],['label','Centered classification'],
          ['v2','V2 limit'],['v3','V3 limit'],['missing_faces','Face without beam'],['narrow_faces','Face with narrow beam'],['reasonLabel','Open issue']],
          page.rows.map(r=>({...r,label:labels[r.enclosure_scenario || r.status] || r.status,
            v2:rounded(r.axes.find(a=>a.axis==='V2')?.calculation?.geometric_limit_kn),
            v3:rounded(r.axes.find(a=>a.axis==='V3')?.calculation?.geometric_limit_kn),reasonLabel:labels[r.reason] || r.reason}))));
        if (member.value) for (const row of page.rows) {
          const details = text('details',''); details.append(text('summary',`${row.end} end · Beam widths and source links`));
          details.append(table([['face','Column face'],['frame_id','Beam'],['native_end','Beam end'],['beam_section_name','Section'],
            ['beam_width_mm','Beam width (mm)'],['column_transverse_width_mm','Column width (mm)']],Object.values(row.faces).filter(Boolean)));
          el('columnContext').append(details);
        }
      } else if (selectedView === 'joint-ties') {
        el('columnUnits').textContent = 'TBDY 7.5.2.3 transfers 40% or 60% of the lower-column confinement reference Ash/s from Eq. (7.1). Areas are in mm² and spacing in mm. Both axial-load branches are shown. Full capacity shear reinforcement requires verification.';
        el('columnContext').append(text('p','The example uses the same Φ12/100 proposal. Upper and lower column axes are mapped to physical directions. Confined and unconfined scenario spacing limits are 150 and 100 mm, respectively. Minimum diameter is 8 mm. Actual joint detailing requires verification.','micro'));
        el('columnForces').append(table([['member_id','End column'],['end','End'],['point_id','Joint'],['lower_column_id','Lower column'],
          ['axis','End direction'],['lower_axis','Lower column direction'],['candidate_label','Longitudinal proposal'],['high','Ash · High N'],
          ['low','Ash · Low N'],['ash','Proposed Ash'],['s','Proposed s'],['reasonLabel','Open issue']],page.rows.map(r=>({...r,
            high:rounded(r.branches.high?.required_ash_at_joint_spacing_mm2),low:rounded(r.branches.low?.required_ash_at_joint_spacing_mm2),
            ash:rounded(r.branches.high?.proposed_ash_mm2),s:r.branches.high?.joint_spacing_mm,
            reasonLabel:labels[r.tie_reason] || r.tie_reason}))));
      } else {
        el('columnUnits').textContent = 'ETABS design-summary references. Exact source identities are required for force selection. PMM and shear compliance remain open.';
        const rows = page.rows.map(r => {
          const refs = Object.fromEntries(r.references.map(ref => [ref.role, ref]));
          const link = role => labels[refs[role]?.status] || refs[role]?.status;
          return {...r.native_design_row, pmmLink:link('PMM'), majorLink:link('MAJOR_SHEAR'), minorLink:link('MINOR_SHEAR')};
        });
        el('columnForces').append(table([['UniqueName','Column'],['Station','Station (m)'],['DesignSect','Design section'],
          ['PMMCombo','PMM combination'],['pmmLink','Source link'],['PMMRatio','ETABS PMM ratio'],
          ['VMajCombo','Major-axis shear'],['majorLink','Source link'],['VMinCombo','Minor-axis shear'],['minorLink','Source link']], rows));
      }
      el('columnPage').textContent = total ? `${offset + 1}–${Math.min(offset + page.limit,total)} / ${total}` : 'No records for this filter and view.';
      el('columnPrevious').disabled = offset === 0;
      el('columnNext').disabled = offset + page.limit >= total;
      const replay = report.static_replay;
      el('columnReplay').append(text('p', `${replay.matched_rows} matching static rows · ${replay.scalar_comparisons} scalar comparisons · Maximum |Δ|: ${replay.maximum_absolute_difference}`));
      el('columnReplay').append(text('p', 'This replay verifies static source arithmetic. Spectral, envelope, and nested combinations require separate demand qualification.', 'micro'));
      el('columnReplay').append(table([['combination','Combination'],['status','Numerical source'],['matched_rows','Matched'],
        ['mismatched_rows','Mismatch'],['unresolved_rows','Unresolved'],['reason','Reason']], replay.combinations));
      el('columnCoverage').append(table([['name','Case / combination'],['row_count','Row'],['members_with_rows','Columns with rows'],
        ['expected_members','Expected'],['step_types','Step'],['step_numbers','Step / mode number'],['missing_members','Missing columns']], report.case_coverage));
      el('columnGaps').append(table([['topic','Work item'],['available','Source'],['remaining','Required evidence']],
        report.engineering_evidence_gaps ?? report.engineering_gaps));
    } catch (error) {
      if (ticket !== epoch || selected !== run.value) return;
      clearResult(); el('columnStatus').textContent = 'Could not display the archive: ' + error.message;
    }
  }
  async function refresh() {
    const ticket = ++historyEpoch; ++epoch; clearResult();
    options(run, [], 'Loading archives…'); options(member, [], 'All columns'); options(loadCase, [], 'All outputs');
    run.disabled = true;
    try {
      const data = await get('/api/column-history');
      if (ticket !== historyEpoch) return;
      options(run, data.runs.map(r => [r.run_id, `${r.run_id} · ${r.force_row_count} rows`]), 'Select an archive');
      el('columnStatus').textContent = data.runs.length ? 'Select the column archive to inspect.' :
        'Import an offline column ZIP to display its archive here.';
    } catch (error) {
      if (ticket === historyEpoch) el('columnStatus').textContent = 'Could not load the archive list:' + error.message;
    } finally { if (ticket === historyEpoch) run.disabled = false; }
  }
  window.openColumnBank = () => { if (!opened) { opened = true; refresh(); } };
  if (typeof active !== 'undefined' && active === 12) window.openColumnBank();
  el('columnRefresh').addEventListener('click', refresh);
  run.addEventListener('change', () => load(true));
  for (const chooser of [member, loadCase, view, proposal, beamProposal].filter(Boolean)) chooser.addEventListener('change', () => { offset = 0; load(); });
  el('columnPrevious').addEventListener('click', () => { offset = Math.max(0, offset - 200); load(); });
  el('columnNext').addEventListener('click', () => { if (offset + 200 < total) { offset += 200; load(); } });
})();
