/* Map verified YENI outputs to the workspace. This layer only selects and formats source fields. */
(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  const workspace = window.TBDYWorkspace;
  const log = window.engineConsole.log;
  const runIdPattern = /^RUN-[0-9a-f]{32}$/;
  const archivedColumn = 'column-127';
  const requestedRun = new URLSearchParams(location.search).get('run');
  const requestedCheck = new URLSearchParams(location.search).get('check');
  const selector = byId('deskRun');
  const probe = byId('deskEtabsProbe');
  const requiredUnits = 'kN·m·°C (API code 6)';
  let requestVersion = 0;
  let busy = false;
  let entries = [];

  const sourceNote = 'Values are from the verified source run. Formal compliance is NOT_PROVEN.';
  const archiveNote = 'Verified archived column calculation. Formal compliance is NOT_PROVEN.';
  const decimals = (value, places = 4) => {
    if (value == null || value === '' || typeof value === 'boolean') return '—';
    const number = Number(value);
    if (!Number.isFinite(number)) return '—';
    const shown = number.toLocaleString('en-GB', {useGrouping: false, maximumFractionDigits: places});
    return shown === '0' && number !== 0 ? number.toExponential(2) : shown;
  };
  const bool = value => value == null ? 'Unavailable' : value ? 'Yes' : 'No';
  const fullCase = (name, status) => name ? name + ' · ' + status : status;
  const table = (headers, rows, status, note = sourceNote, inputs) =>
    ({headers, rows, status, note, inputs});
  const capturedRows = entry => entry?.status === 'CAPTURED' && Array.isArray(entry.rows) ? entry.rows : [];
  const sourceValue = value => value == null || value === '' || value === 'None' ? null : value;
  const checkOf = (report, id) => report.checks?.find(check => check.check_id === id);
  const sections = (rows, keys) => rows.map(row => keys.map(key => row[key]));
  const membersByStory = row => (row.members_by_story ?? [])
    .map(group => (group.story ?? 'Unknown story') + ': ' + group.member_ids_text).join('\n');
  const sourceUrl = (path, runId) => path + '?run_id=' + encodeURIComponent(runId);

  function analysisTable(setup) {
    if (!setup) return undefined;
    return table(['Case', 'ETABS stiffness setting', 'Initial nonlinear case'],
      sections(setup.linear_static_settings ?? [], ['case', 'stiffness_setting', 'nonlinear_case']),
      'Analysis authority pending', 'ETABS stiffness settings and design selections are source observations. Analysis generation and project load roles require approval.',
      [['Case definitions', setup.case_definition_count], ['Combination definitions', setup.defined_combination_names.length],
        ['ETABS design selections', setup.design_selection_count], ['Analysis generation verified', bool(setup.analysis_generation_proven)]]);
  }

  function projectDetails(report) {
    const source = report.source_snapshot ?? {};
    const recordedUnits = report.capture_metadata?.etabs_session?.units_label
      ?? (source.geometry_capture?.present_units === 6 && source.geometry_capture?.present_units_after === 6
        ? 'kN·m·°C' : null);
    const families = new Map([
      ['Column', new Map()], ['Beam', new Map()], ['Wall', new Map()], ['ETABS slab-type area', new Map()],
    ]);
    function add(family, name, material) {
      if (!name || name === 'None') return;
      const rows = families.get(family);
      const nameAndMaterial = JSON.stringify([name, sourceValue(material)]);
      const row = rows.get(nameAndMaterial) ?? {name, material: sourceValue(material), count: 0};
      row.count++;
      rows.set(nameAndMaterial, row);
    }
    for (const [family, id] of [['Column', 'column_rect_min'], ['Beam', 'beam_width_min']]) {
      for (const row of checkOf(report, id)?.items ?? []) add(family, row.assigned_section, row.material_name);
    }
    const area = source.vs06_b1_geometry_source?.table_reads ?? {};
    const walls = new Map(capturedRows(area['Wall Property Definitions - Specified']).map(row => [row.Name, row.Material]));
    for (const row of capturedRows(area['Area Assignments - Section Properties'])) {
      if (row.PropType === 'Wall') add('Wall', row.SectProp, walls.get(row.SectProp));
      if (row.PropType === 'Slab') add('ETABS slab-type area', row.SectProp, null);
    }
    const summary = Array.from(families, ([family, records]) => [...records.values()].map(row =>
      [family, row.name, row.count, row.material])).flat();
    const concreteNames = type => [...new Set((report.material_member_groups ?? []).filter(row =>
      row.member_type === type && row.material_classification === 'RESOLVED_CONCRETE_USAGE')
      .map(row => row.material_name))].join(', ') || null;
    const story = report.physical_story_scope;
    return {
      groups: [
        ['Project identification', [['ETABS model', report.model], ['Captured ETABS units', recordedUnits],
          ['Latitude (°)', null], ['Longitude (°)', null],
          ['Province', null], ['District', null], ['Neighborhood', null], ['Map sheet', null],
          ['Block', null], ['Parcel', null], ['Total floor area (m²)', null]]],
        ['Structural materials', [['Column concrete', concreteNames('Column')], ['Beam concrete', concreteNames('Beam')],
          ['Wall concrete', [...new Set([...families.get('Wall').values()].map(row => row.material).filter(Boolean))].join(', ') || null],
          ['Slab concrete', null], ['Foundation concrete', null], ['Reinforcement grade', null]]],
        ['Concrete cover (cm)', ['Column', 'Beam', 'Wall', 'Slab', 'Foundation'].map(name => [name, null])],
      ],
      table: table(['Member type', 'Assigned ETABS section', 'Objects', 'Source material'], summary,
        'Source inventory', 'Counts describe assignments in the selected capture. A complete structural system classification requires a verified model profile.'),
      facts: [['Physical stories', story?.physical_story_count], ['Defined stories', story?.defined_story_count],
        ['Model profile', report.analysis_setup?.model_profile_approved ? 'Approved' : 'NOT_PROVEN']],
    };
  }

  function spectrumDetails(report) {
    const basis = report.source_snapshot?.vs04_basis_probe?.table_reads ?? {};
    const rows = capturedRows(basis['Functions - Response Spectrum - TSC-2018']);
    const recordedCases = capturedRows(basis['Load Case Definitions - Response Spectrum']);
    const reconstruction = report.vs04_pipeline?.stages?.vs04_i;
    const series = new Map();
    for (const row of rows) {
      if (!row.Name) continue;
      let item = series.get(row.Name);
      if (!item) {
        item = {name: row.Name, parameters: {}, points: []};
        series.set(row.Name, item);
      }
      for (const key of ['Direction', 'SiteClass', 'R', 'D', 'I', 'Ss', 'S1', 'Fs', 'F1', 'SDS', 'SD1', 'TL', 'DampRatio']) {
        if (sourceValue(row[key]) === null || item.parameters[key] === 'Conflicting source values') continue;
        item.parameters[key] = item.parameters[key] == null || item.parameters[key] === row[key]
          ? row[key] : 'Conflicting source values';
      }
      if (sourceValue(row.Period) !== null && sourceValue(row.Value) !== null) {
        const period = Number(row.Period), value = Number(row.Value);
        if (Number.isFinite(period) && period >= 0 && Number.isFinite(value) && value >= 0) item.points.push([period, value]);
      }
    }
    const available = [...series.values()];
    for (const item of available) {
      item.points.sort((a, b) => a[0] - b[0]);
      item.cases = recordedCases.filter(row => row.Function === item.name);
    }
    return {
      functions: available,
      cornerPeriods: available.length === 1 ? reconstruction?.derived_corner_periods_s : null,
    };
  }

  function runTables(report) {
    const snapshot = report.source_snapshot, geometry = snapshot?.geometry_capture?.tables ?? {};
    const basis = snapshot?.vs04_basis_probe?.table_reads ?? {};
    const stages = report.vs04_pipeline?.stages ?? {};
    const summaries = capturedRows(geometry.SECTION_SUMMARY);
    const rects = capturedRows(geometry.RECTANGULAR_SECTIONS);
    const rectByName = new Map(rects.map(row => [row.Name, row]));
    const assignments = capturedRows(geometry.SECTION_ASSIGNMENTS);
    const materials = report.geometry_source_summary?.material_types?.facts ?? {};
    const mass = capturedRows(basis['Mass Source Definition']);
    const spectrum = capturedRows(basis['Functions - Response Spectrum - TSC-2018']);
    const physical = report.physical_story_scope, modal = checkOf(report, 'modal_mass_95');
    const baseShear = stages.vs04_j;
    const drift = report.story_drift, r08 = report.r08_second_order;
    const wall = report.wall_geometry;
    const observed = 'Source observed';
    const tables = {};
    if (physical?.stories?.length) {
      tables['1.1'] = table(['Story', 'Top elevation (m)', 'Height (m)', 'Frames', 'Areas', 'Walls', 'Joints', 'Applicability'],
        sections(physical.stories, ['story', 'upper_elevation_m', 'height_m', 'frames', 'areas', 'walls', 'joints', 'applicability']),
        physical.source_inventory_complete ? 'Inventory verified' : 'Partial inventory',
        'An empty story is excluded when the complete source inventory confirms it.', [
          ['Defined stories', physical.defined_story_count], ['Physical stories', physical.physical_story_count],
          ['Source units', report.geometry_source_summary?.source_units],
        ]);
    } else {
      const stories = capturedRows(basis['Story Definitions']);
      if (stories.length) tables['1.1'] = table(['Story', 'Height (m)', 'Tower'],
        sections(stories, ['Story', 'Height', 'Tower']), observed);
    }
    if (Object.keys(materials).length) {
      const min = checkOf(report, 'concrete_fck_25');
      const strength = new Map((min?.items ?? []).map(row => [row.material_name, row]));
      const upperCheck = report.source_controls?.checks?.find(check => check.check_id === 'concrete_fck_80');
      const upper = new Map((upperCheck?.items ?? []).map(row => [row.material_name, row]));
      const roster = [...(report.material_member_groups ?? [])];
      const linkedNames = new Set(roster.map(row => row.material_name));
      for (const name of Object.keys(materials)) {
        if (!linkedNames.has(name)) roster.push({material_name: name});
      }
      tables['1.2'] = table(['Material', 'Member type', 'Members', 'ETABS Unique IDs by story', 'Material link',
        'Observed fck (MPa)', 'fck ≥ 25 MPa', 'fck ≤ 80 MPa'], roster.map(group => {
        const name = group.material_name, lower = strength.get(name), cap = upper.get(name);
        return [name, group.member_type, group.member_count, membersByStory(group),
          group.material_classification ?? materials[name]?.status, decimals(lower?.fck_mpa ?? cap?.fck_mpa),
          lower?.status, cap?.status];
      }), observed, 'Each column and beam is counted once in the material roster. Strength checks apply to the recorded material values.');
    }
    if (summaries.length) tables['1.3'] = table(['Section', 'Source shape', 'Material', 'Native t2 (m)', 'Native t3 (m)'],
      summaries.map(row => [row.Name, row.Shape, row.Material, rectByName.get(row.Name)?.t2, rectByName.get(row.Name)?.t3]), observed);
    if (assignments.length) tables['1.4'] = table(['Story', 'ETABS Unique ID', 'ETABS label', 'Shape', 'Assigned section'],
      sections(assignments, ['Story', 'UniqueName', 'Label', 'Shape', 'SectProp']), observed,
      'These are native section assignments. Unresolved member, section or material links are assessed by the relevant geometry check.');
    if (mass.length) tables['1.5'] = table(['Mass source', 'Default', 'Load pattern', 'Multiplier', 'Self mass'],
      sections(mass, ['Name', 'IsDefault', 'LoadPattern', 'Multiplier', 'SourceSelf']), observed,
      'Mass source factors are observed. Project load roles and seismic mass scope require separate approval.');
    if (report.analysis_setup) tables['1.6'] = analysisTable(report.analysis_setup);
    if (rects.length) tables['1.7'] = table(['Section', 'Design type', 'Area factor', 'Torsion factor', 'I2 factor', 'I3 factor'],
      sections(rects, ['Name', 'DesignType', 'AMod', 'JMod', 'I2Mod', 'I3Mod']), observed,
      'These factors come from ETABS section definitions. Effective object modifiers and use in the analysis require separate evidence.');
    if (spectrum.length) tables['2.1'] = table(['Function', 'Period (s)', 'ETABS ordinate', 'SDS', 'SD1', 'Site class'],
      sections(spectrum, ['Name', 'Period', 'Value', 'SDS', 'SD1', 'SiteClass']), observed,
      'This table shows the captured ETABS TSC-2018 function values. Hazard input approval and scaling are separate checks.');
    if (modal) tables['2.2'] = table(['Case', 'Participating mass X', 'Participating mass Y', 'Required ratio', 'Governing mode count', 'Status'],
      [[modal.case, decimals(modal.sum_ux), decimals(modal.sum_uy), decimals(modal.required_ratio), modal.governing_mode_count, modal.status]],
      modal.status, 'The calculation checks the effective modal mass ratio. Formal compliance is NOT_PROVEN.',
      [['Modal source rows', report.modal_source_table?.row_count]]);
    if (baseShear?.conditional_eq_4_19_minimum_term_kn != null) {
      const reactions = baseShear.source_case_base_reaction_components_kn ?? {};
      tables['2.3'] = table(['Source quantity', 'Value (kN)'], [
        ['Eq. 4.19 conditional lower-bound term', decimals(baseShear.conditional_eq_4_19_minimum_term_kn, 2)],
        ...Object.entries(reactions).map(([name, value]) => [name, decimals(value, 2)]),
        ['Full equivalent base shear VtE', baseShear.full_equivalent_base_shear_kn],
      ], 'Conditional source screening', 'Full equivalent base shear and βtE scaling require further evidence.');
    }
    if (drift?.items?.length) tables['3.1'] = table(
      ['Story', 'Case', 'Direction', 'Story height (m)', 'ETABS drift ratio', 'Derived Δ (mm)', 'Status'],
      drift.items.map(row => [row.story, row.case, row.direction, row.height_m,
        decimals(row.etabs_story_drift_ratio, 6), decimals(row.etabs_derived_delta_mm, 4), row.regulatory_status]),
      drift.status, 'ETABS Drift × story height gives a source displacement. Code effective drift requires project input and concurrence evidence.', [
        ['Recorded ETABS cases', [...new Set(drift.items.map(row => row.case))].join(', ')],
        ['Evaluated rows', drift.evaluated_story_case_direction_count], ['Expected rows', drift.expected_story_case_direction_count],
        ['Excluded verified empty stories', (drift.excluded_stories ?? []).map(row => row.story).join(', ') || 'None'],
      ]);
    if (r08?.results?.length) tables['3.2'] = table(
      ['Story', 'Case', 'Direction', 'Average Δ (m)', 'Reduced V (kN)', 'Candidate θII', 'Status'],
      r08.results.map(row => [row.story, row.case, row.direction, decimals(row.etabs_avg_drift_m_candidate, 6),
        decimals(row.reduced_story_shear_kn_candidate, 2), decimals(row.theta_ii_candidate, 6), row.source_numeric_status]),
      'Conditional source calculation', 'Design force magnification requires approved design authority and analysis generation.',
      [['Recorded ETABS cases', [r08.configuration?.x_case, r08.configuration?.y_case].filter(Boolean).join(', ')],
        ['Recorded weight combination', r08.configuration?.weight_combo],
        ['Story-direction coverage', r08.evaluated_story_direction_count + '/' + r08.expected_story_direction_count],
        ['Maximum θII X', decimals(r08.direction_results?.X?.theta_max_candidate, 6)],
        ['Maximum θII Y', decimals(r08.direction_results?.Y?.theta_max_candidate, 6)],
        ['Excluded verified empty stories', (r08.excluded_stories ?? []).map(row => row.story).join(', ') || 'None']]);
    else if (r08) tables['3.2'] = table(['Source issue'], (r08.reason_codes ?? []).map(reason => [reason]), r08.status,
      'Global second-order source rows are unavailable for this capture.');
    for (const [id, ids] of [['4.1', ['column_rect_min']], ['5.1', ['beam_width_min', 'beam_depth_min', 'beam_depth_width']]]) {
      const checks = ids.map(key => checkOf(report, key)).filter(Boolean);
      if (!checks.length) continue;
      tables[id] = table(['Check', 'Assigned section', 'Material', 't2 (mm)', 't3 (mm)', 'Members',
        'ETABS Unique IDs by story', 'Value', 'Limit', 'Ratio', 'Diagnostic', 'Status'], checks.flatMap(check =>
        (check.member_groups ?? []).map(row => [check.title, row.assigned_section ?? row.section, row.material_name,
          decimals(row.width_mm, 2), decimals(row.depth_mm, 2), row.member_count, membersByStory(row),
          decimals(row.value), decimals(row.limit), decimals(row.ratio), row.reason, row.status])),
        'Numerical geometry checks', 'Groups share the same inputs and result within a check. The source JSON lists each member separately.');
    }
    const axial = report.column_axial;
    if (axial) {
      const sources = {ASSIGNED_DESIGN: 'Assigned design combinations', ETABS_STRENGTH: 'ETABS Strength selections',
        SAVED_DEFAULTS: 'Recorded custom combination list'};
      tables['4.3'] = table(
        ['Story', 'ETABS Unique ID', 'Section', 'Material', 'Governing observed combination', 'Object station (m)',
          'Analysis element ID', 'Element station (m)', 'Step', 'Nd (kN)', 'TS 500 limit (kN)', 'Nd / limit', 'Status', 'Evidence gap'],
        axial.columns.map(row => {
          const governing = row.governing;
          const blocked = row.combination_checks?.filter(item => item.status === 'BLOCKED') ?? [];
          return [row.story, row.element_id, row.section, row.material_name, governing?.combination,
            decimals(governing?.object_station_m), governing?.analysis_element, decimals(governing?.element_station_m),
            governing?.step_type, decimals(governing?.nd_kn), decimals(row.ts500_limit_kn),
            decimals(governing?.ratio), row.status, row.reason || blocked.map(item => item.combination + ' · ' + item.reason).join('\n')];
        }),
        axial.status, axial.combination_plan.blockers.join(' · ') ||
          'TS 500 Eq. (7.7) numerical results for the captured combinations and stations. TBDY seismic applicability and project approval remain open.',
        [['Run combination source', sources[axial.combination_plan.source]],
          ['ETABS combinations in this run', axial.combination_plan.combinations.map(item => item.name).join(', ')],
          ['Completed columns', axial.completed_column_count + ' / ' + axial.expected_column_count],
          ['Evaluated column–combination pairs', axial.evaluated_member_combination_count + ' / ' + axial.expected_member_combination_count],
          ['Native rows', axial.native_force_row_count], ['Columns with observed exceedance', axial.observed_exceedance_count],
          ['Concrete factor γc', decimals(axial.gamma_c)]]);
    }
    if (wall?.items?.length) tables['7.1'] = table(['Story', 'ETABS Unique ID', 'Section', 'Panel length (m)', 'Thickness (mm)', 'Length/thickness', 'Status'],
      wall.items.map(row => [row.story, row.element_id, row.section, decimals(row.panel_length_m),
        decimals(row.thickness_mm), decimals(row.panel_length_thickness_ratio), row.status]),
      wall.status, 'These dimensions describe ETABS area panels. The complete physical wall or leg length requires verification.');
    return tables;
  }

  function irregularityTables(report) {
    const out = {};
    const torsion = ['a1_torsion_x', 'a1_torsion_y'].map(id => checkOf(report, id)).filter(Boolean);
    const b1 = report.vs06_b1_result?.b1_numerical, b2 = report.soft_story_b2;
    if (torsion.length) out.A1 = table(['Story', 'Direction', 'Case', 'ηbi', 'Limit', 'Status'],
      torsion.flatMap(check => (check.items ?? []).map(row =>
        [row.story, row.direction, row.source_case, decimals(row.eta_bi), decimals(row.limit), row.status])),
      'Source classification', 'Eccentricity application and code coverage require further evidence.');
    if (b1?.paired_results?.length) out.B1 = table(['Lower story', 'Upper story', 'Direction', 'Lower Ae (m²)', 'Upper Ae (m²)', 'ηci', 'Status'],
      b1.paired_results.map(row => [row.lower_story, row.upper_story, row.direction,
        decimals(row.Ae_lower_m2), decimals(row.Ae_upper_m2), decimals(row.eta_ci), row.numeric_condition]),
      'Conditional source calculation', 'Calculated with assumed infill area. Code B1 determination remains open.');
    if (b2?.items?.length) out.B2 = table(['Story', 'Adjacent story', 'Direction', 'Case', 'Candidate ηki', 'Threshold', 'Status'],
      b2.items.map(row => [row.story, row.adjacent_story, row.direction, row.case,
        decimals(row.eta_ki_candidate), decimals(row.threshold), row.status]),
      'Conditional source calculation', 'Uses source Avg Drift / h. Code B2 determination remains open.');
    return out;
  }

  function presentRun(report, runId) {
    if (report.run_id !== runId || report.schema !== 'tbdy.next.complete.engineering.report.v1' ||
        report.formal_compliance !== 'NOT_PROVEN' || report.engineering_release !== 'NOT_READY' ||
        !/^[a-f0-9]{64}$/.test(report.source_provenance?.input_sha256)) {
      throw new Error('The report failed the workspace source contract.');
    }
    return {
      modelName: report.model || 'Archived ETABS source', runId,
      modelKey: report.source_snapshot?.source_identity && report.physical_story_scope?.geometry_fingerprint
        ? report.source_snapshot.source_identity + ':' + report.physical_story_scope.geometry_fingerprint
        : report.source_snapshot?.source_identity || 'run:' + runId,
      sourceSha: report.source_provenance.input_sha256,
      sourceLabel: fullCase(report.modal_case, report.source_mode === 'LIVE_ETABS' ? 'Saved live capture' : 'Saved source run'),
      reportUrl: sourceUrl('/report/print', runId), jsonUrl: sourceUrl('/api/export-checks', runId),
      analysisSetup: report.analysis_setup,
      designAssignments: report.design_assignments,
      columnStrengthAvailable: report.source_mode === 'LIVE_ETABS' && report.analysis_setup?.definition_coverage_known === true,
      columnForces: report.column_axial ? {
        rowsets: report.source_snapshot?.column_axial?.force_source?.rowsets ?? {},
        combinations: report.column_axial.combination_plan.combinations,
      } : null,
      project: projectDetails(report), seismic: spectrumDetails(report),
      tables: runTables(report), irregularities: irregularityTables(report),
    };
  }
  function presentColumn(payload) {
    const p0 = payload.p0_gate_report, receipt = payload.reconciled;
    if (payload.source_mode !== 'ARCHIVED_COLUMN_RECEIPT' || !p0?.p0b_gates || !receipt?.r08?.geometry ||
        p0.baseline_reconciled_sha256 !== receipt.result_sha256 ||
        p0.verdict_summary?.formal_compliance !== 'NOT_PROVEN' ||
        receipt.engineering_release !== 'NOT_READY') {
      throw new Error('The archived column source failed verification.');
    }
    const gates = p0.p0b_gates, geom = receipt.r08.geometry, material = payload.source_context;
    const setup = p0.p0c_model_analysis_setup_audit;
    const {local2_extent_mm: local2, local3_extent_mm: local3} = p0.local_dims_mm;
    const proposals = Object.values(gates.f03_reinforcement_states).filter(row => ['TEMPLATE', 'PROPOSED'].includes(row.role));
    const stations = gates.f02_grav_ult_stations;
    const seismic = gates.f01_axial_caps_summary.checks['CHK-004'];
    const tableMap = {
      '1.1': table(['ETABS Unique ID', 'ETABS label', 'Story', 'Joint-to-joint length (m)'],
        [[p0.member, p0.label, p0.story, decimals(geom.length_i_j_m)]], 'Archived member evidence', archiveNote),
      '1.2': table(['Concrete', 'Observed fck (MPa)', 'Scenario fcd (MPa)', 'Scenario fyd (MPa)'],
        [[material.concrete_material, decimals(material.material_owner.fck, 3),
          decimals(material.material_owner.fcd, 3), decimals(material.material_owner.fyd, 3)]], 'Archived member evidence', archiveNote),
      '1.6': analysisTable(setup),
      '4.1': table(['ETABS Unique ID', 'Story', 'Section', 'Local 2 (mm)', 'Local 3 (mm)'],
        [[p0.member, p0.story, p0.section_name, local2, local3]], 'Archived member geometry',
        'Verified local dimensions for the archived column. Numerical geometry coverage for the whole model is available in its own source run.'),
      '4.2': table(['Role', 'Reinforcement', 'Ratio', 'Minimum ratio', 'Maximum ratio', 'Status'],
        proposals.map(row => [row.role, row.bar_count + 'Φ' + row.bar_diameter_mm, decimals(row.rho, 6),
          row.rho_min, row.rho_max, row.status]),
        'Conditional reinforcement checks', 'The ETABS template and the proposed cage are evaluated as separate scenarios. Selection and installation evidence are pending.'),
      '4.3': table(['Criterion', 'Combination', 'Station (m)', 'Nd (kN)', 'Limit (kN)', 'Utilization', 'Status'], [
        ...stations.map(station => {
          const item = station.axial_cap_gate.checks['CHK-005'];
          return ['CHK-005', receipt.case, decimals(station.object_station_m), decimals(item.nd_kn, 2),
            decimals(item.limit_kn, 2), decimals(item.utilization_ratio, 4), item.exceeded ? 'FAIL' : 'MEETS_NUMERICAL_CRITERION'];
        }),
        ['CHK-004', 'Seismic demand', null, null, decimals(seismic.limit_kn, 2), null,
          seismic.applicable_to_combo === false ? 'NOT_APPLICABLE' : 'NOT_PROVEN'],
      ], 'Conditional axial checks', 'The archived demand is from the gravity combination. Seismic axial demand is pending.', [
        ['Section', local2 + ' × ' + local3 + ' mm'], ['Compressive strength fck (MPa)', decimals(material.material_owner.fck, 3)],
        ['Design strength fcd (MPa)', decimals(material.material_owner.fcd, 3)],
      ]),
      '4.4': table(['Station (m)', 'Combination', 'Raw PMM', 'PMM with minimum eccentricity', 'Status'],
        stations.map(row => [decimals(row.object_station_m), receipt.case, decimals(row.raw_pmm_utilization, 5),
          decimals(row.pmm_with_e_min_utilization, 5), row.pmm_with_e_min_status]),
        'Proposed reinforcement scenario', 'PMM uses the archived proposed cage. Engineering design acceptance is pending.', [
          ['Minimum eccentricity about local 2 (mm)', decimals(gates.f02_lc_dl_station0_e_min.e_min_gate.e_min_m2_mm, 2)],
          ['Minimum eccentricity about local 3 (mm)', decimals(gates.f02_lc_dl_station0_e_min.e_min_gate.e_min_m3_mm, 2)],
        ]),
      '4.5': table(['Check', 'Archived evidence'], [
        ['Global P–Δ', receipt.r08.global_p_delta],
        ['Local P–δ', receipt.r08.local_p_delta],
      ], 'NOT_PROVEN', 'Moment magnification requires verified clear length, effective length factor, stiffness and analysis basis.', [
        ['Joint-to-joint length (m)', decimals(geom.length_i_j_m)],
        ['Output-face spacing (m)', decimals(geom.observed_output_span_m)],
        ['Clear length ln (mm)', decimals(geom.free_length_ln_mm)],
        ['Effective length factor k', decimals(geom.effective_length_factor_k)],
      ]),
      '4.6': table(['Role', 'Maximum ai (mm)', 'Limit ai (mm)', 'Spacing s (mm)', 'Limit s (mm)', 'Status'],
        Object.entries(gates.f07_transverse_topology).map(([name, row]) => [
          name.startsWith('etabs') ? 'ETABS template' : 'Proposed · ' + row.leg_count_per_axis + ' legs per axis',
          decimals(row.max_ai_mm ?? row.perimeter_hoop_only_ai_mm, 1), decimals(row.ai_limit_25_phi_e_mm, 1),
          row.vertical_spacing_s_mm, row.s_max_limit_mm, row.status,
        ]), 'Conditional topology checks', 'Leg spacing and tie spacing come from the F07 receipt. The proposed topology requires engineering approval.'),
    };
    return {
      modelName: material.model_name, sourceLabel: 'Archived column receipt',
      modelKey: 'column:' + receipt.source_model_sha256, sourceSha: p0.result_sha256,
      reportUrl: '/report/column-127', jsonUrl: '/api/column-127-gates',
      analysisSetup: setup, designAssignments: payload.design_assignments, reconciled: receipt, p0_gate_report: p0, tables: tableMap,
    };
  }

  async function json(url, options) {
    const response = await fetch(url, {cache: 'no-store', ...options});
    const body = await response.json();
    if (!response.ok) {
      const error = new Error(body.result?.reason || body.reason || body.error || 'HTTP ' + response.status);
      error.etabsSession = body.etabs_session;
      throw error;
    }
    return body;
  }

  async function fetchSource(id) {
    if (id === archivedColumn) return presentColumn(await json('/api/column-127-workspace'));
    if (!runIdPattern.test(id)) throw new Error('Select a verified source run.');
    return presentRun(await json(sourceUrl('/api/export-checks', id)), id);
  }

  function setRunStatus(message, error = false) {
    const status = byId('deskRunStatus');
    status.textContent = message;
    status.classList.toggle('error', error);
  }

  function showEtabsConnection(session, message) {
    const info = byId('deskEtabsUnits');
    const container = byId('deskEtabsConnection');
    if (!session) {
      info.textContent = [message, 'Required ETABS units ' + requiredUnits].filter(Boolean).join(' · ');
      container.classList.toggle('error', Boolean(message) && message !== 'Connecting to ETABS…');
      return;
    }
    const matches = session.units_code === 6 && session.units_api_agree !== false;
    const target = session.process_id ? 'PID ' + session.process_id : 'Active instance';
    const code = Number.isInteger(session.units_code) ? ' (API code ' + session.units_code + ')' : '';
    const units = (session.units_label || 'Units unavailable') + code;
    info.textContent = [session.model_name, target, units, session.model_locked ? 'Locked' : 'Unlocked',
      session.units_api_agree === false && 'API unit methods disagree',
      !matches && 'Required ' + requiredUnits,
      message].filter(Boolean).join(' · ');
    container.classList.toggle('error', !matches || !session.model_locked);
  }

  function chooseRun(id) {
    if (selector.value !== id) selector.value = id;
    const params = new URLSearchParams(location.search);
    if (id) params.set('run', id);
    else params.delete('run');
    history.replaceState(null, '', location.pathname + (params.size ? '?' + params : ''));
  }

  function renderPicker(selected = '') {
    const choices = [['', 'Select a verified source'], ...entries.map(row => [
      row.run_id, [row.model_name || 'ETABS archive', row.case,
        row.captured_at_utc && row.captured_at_utc.slice(0, 16).replace('T', ' ') + ' UTC',
        row.run_id.slice(-8)].filter(Boolean).join(' · '),
    ]), [archivedColumn, 'Archived column 127 / C88']];
    selector.replaceChildren(...choices.map(([id, title]) => {
      const option = document.createElement('option');
      option.value = id;
      option.textContent = title;
      return option;
    }));
    selector.value = selected;
  }

  async function activateSource(id) {
    const version = ++requestVersion;
    workspace.setData(null);
    byId('deskLoadStatus').textContent = '';
    if (!id) {
      chooseRun('');
      setRunStatus('Select a saved run or read the open ETABS model.');
      return;
    }
    setRunStatus('Verifying the selected source…');
    try {
      const result = await fetchSource(id);
      if (version !== requestVersion) return;
      workspace.setData(result);
      if (id === archivedColumn) workspace.openCheck('4.3');
      const entry = entries.find(row => row.run_id === id);
      if (entry?.case) byId('deskModalCase').value = entry.case;
      chooseRun(id);
      setRunStatus(result.sourceLabel + ' · ' + result.modelName);
    } catch (error) {
      if (version !== requestVersion) return;
      setRunStatus('Could not load the selected source. ' + error.message, true);
      log('error', 'SOURCE', error.message);
    }
  }

  workspace.setLoader(async () => {
    const source = selector.value;
    try {
      return await fetchSource(source);
    } catch (error) {
      if (source === selector.value) setRunStatus('Saved source verification failed. ' + error.message, true);
      throw error;
    }
  });
  selector.addEventListener('change', () => activateSource(selector.value));

  probe.addEventListener('click', async () => {
    if (busy) return;
    busy = true;
    probe.disabled = true;
    byId('deskLive').disabled = true;
    showEtabsConnection(null, 'Connecting to ETABS…');
    try {
      const body = await json('/api/etabs-session', {method: 'POST'});
      showEtabsConnection(body.etabs_session);
    } catch (error) {
      showEtabsConnection(error.etabsSession, error.message);
    } finally {
      probe.disabled = false;
      byId('deskLive').disabled = false;
      busy = false;
    }
  });

  window.addEventListener('tbdy:open-source', event => {
    const {legacyTab, runId, checkId} = event.detail;
    const params = new URLSearchParams({tab: legacyTab});
    const columnView = {
      '4.2': 'reinforcement', '4.4': 'pmm', '4.5': 'length-sensitivity', '4.6': 'transverse',
      '4.7': 'shear', '4.8': 'scwb', '5.2': 'beam-cages', '6.1': 'joints', '6.3': 'joints',
    }[checkId];
    if (columnView) {
      params.set('tab', 12);
      params.set('column_view', columnView);
    }
    if (runIdPattern.test(runId)) params.set('run', runId);
    if (selector.value === archivedColumn) {
      if (columnView && !['4.2', '4.4', '4.5', '4.6'].includes(checkId)) {
        location.assign('/source?' + new URLSearchParams({tab: 12, column_view: columnView}));
      } else {
        location.assign('/report/column-127');
      }
      return;
    }
    location.assign('/source?' + params);
  });

  async function runLive(columnStrength = null) {
    if (busy) return;
    const modal = byId('deskModalCase').value.trim();
    if (!modal) {
      setRunStatus('Enter the exact ETABS modal case name.', true);
      return;
    }
    busy = true;
    requestVersion++;
    selector.disabled = true;
    byId('deskLive').disabled = true;
    probe.disabled = true;
    workspace.setLiveBusy(true);
    byId('deskLoadStatus').textContent = '';
    setRunStatus(columnStrength ? 'Reading the selected ETABS frame forces and checking axial compression…' :
      'Reading the locked ETABS model and evaluating the combined checks…');
    log('info', 'ETABS', (columnStrength ? 'Column axial capture started · ' : 'Combined live scan started · ') + modal);
    try {
      const query = new URLSearchParams();
      if (columnStrength) {
        query.set('check', 'column-axial');
        query.set('base_run_id', selector.value);
        query.set('combination_source', columnStrength.source);
        if (columnStrength.source === 'ASSIGNED_DESIGN') {
          query.set('assignments', JSON.stringify(columnStrength.groups));
        } else if (columnStrength.source === 'SAVED_DEFAULTS') {
          for (const name of columnStrength.defaults) query.append('combination', name);
        }
      }
      const suffix = query.size ? '&' + query : '';
      const body = await json('/api/live-vs04?case=' + encodeURIComponent(modal) + suffix, {method: 'POST'});
      showEtabsConnection(body.etabs_session_after_scan ?? body.etabs_session);
      if (!runIdPattern.test(body.run_id) || body.formal_compliance !== 'NOT_PROVEN' ||
          body.engineering_release !== 'NOT_READY' || body.vs04_pipeline?.pipeline_contract_version !== 'v2') {
        throw new Error('The capture did not return a verified combined run.');
      }
      if (columnStrength && !body.column_axial) {
        throw new Error('Restart the local YENI server to enable the column force check.');
      }
      const entry = {
        run_id: body.run_id, model_name: body.model_name, case: modal,
        captured_at_utc: new Date().toISOString(), source_mode: 'LIVE_ETABS',
      };
      entries = [entry, ...entries.filter(row => row.run_id !== entry.run_id)];
      renderPicker(entry.run_id);
      log('success', 'ETABS', 'Saved combined run ' + entry.run_id);
      if (body.column_axial) {
        const axial = body.column_axial;
        log(axial.status === 'NUMERICAL_COMPLETE' ? 'info' : 'warn', 'COLUMN AXIAL',
          axial.completed_column_count + '/' + axial.expected_column_count + ' columns · ' +
          axial.native_force_row_count + ' force rows · ' + axial.status);
      }
      if (body.analysis_setup?.blocker_codes?.length) {
        log('warn', 'R03 ANALYSIS SETUP', body.analysis_setup.blocker_codes.join(' · '));
      }
      const second = body.r08_second_order;
      if (second) {
        log(second.reason_codes?.length ? 'warn' : 'info', 'R08 GLOBAL P–Δ',
          second.evaluated_story_direction_count + '/' + second.expected_story_direction_count + ' story-directions · ' +
          [second.status, ...(second.reason_codes ?? [])].join(' · '));
        if (second.source_capture_error) log('error', 'R08 SOURCE', second.source_capture_error);
      }
      await activateSource(body.run_id);
    } catch (error) {
      showEtabsConnection(error.etabsSession, error.etabsSession ? null : 'Live connection unavailable');
      if (error.message.includes('LIVE_ETABS_UNITS_KN_M_C_REQUIRED')) {
        log('warn', 'ETABS UNITS', 'The scan requires kN·m·°C from the ETABS API (code 6). Check the connected model and its API units.');
      }
      log('error', 'COMBINED SCAN', error.message);
      setRunStatus('ETABS capture failed. ' + error.message, true);
    } finally {
      busy = false;
      selector.disabled = false;
      byId('deskLive').disabled = false;
      probe.disabled = false;
      workspace.setLiveBusy(false);
    }
  }

  byId('deskRunForm').addEventListener('submit', event => {
    event.preventDefault();
    runLive();
  });
  byId('deskReadColumnForces').addEventListener('click', () => {
    runLive(workspace.getState().assignments.columnStrength);
  });

  async function start() {
    byId('deskLive').disabled = true;
    probe.disabled = true;
    try {
      const data = await json('/api/quick-history?view=summary');
      entries = Array.isArray(data.runs) ? data.runs.filter(entry => runIdPattern.test(entry.run_id)) : [];
      const first = requestedRun === archivedColumn || runIdPattern.test(requestedRun)
        ? requestedRun : entries[0]?.run_id;
      if (runIdPattern.test(first) && !entries.some(row => row.run_id === first)) {
        entries.push({run_id: first});
      }
      renderPicker(first);
      await activateSource(first);
      if (requestedCheck) workspace.openCheck(requestedCheck);
    } catch (error) {
      renderPicker();
      setRunStatus('Could not load run history. ' + error.message, true);
      log('error', 'RUN HISTORY', error.message);
    } finally {
      selector.disabled = false;
      byId('deskLive').disabled = false;
      probe.disabled = false;
    }
  }
  start();
})();
