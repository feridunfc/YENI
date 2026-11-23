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

  function addWallTables(tables, building) {
    const sections = building?.wall_sections;
    const boundaries = building?.wall_boundaries;
    const piers = sections?.piers ?? [];
    const percentage = ratio => Number.isFinite(ratio) ? decimals(100 * ratio, 2) : '—';
    const limits = interval => Array.isArray(interval) && interval.length === 2
      ? interval.map(value => decimals(value, 2)).join(' to ') : '—';
    const rowsFor = (field, format) => piers.flatMap(pier =>
      (pier[field] ?? []).map(row => [pier.pier, ...format(row, pier)]));
    const coverage = (value, total, scope) => Number.isInteger(value) && Number.isInteger(total)
      ? value + '/' + total + ' ' + scope : 'Recorded results';
    const cut = row => [row.member, row.story, row.face, row.combination];
    const headers = ['Pier', 'Wall ID', 'Storey', 'Face', 'Combination'];
    const basis = 'Proposed reinforcement and native assigned combinations. ';
    const status = row => row.reason || row.status;

    if (boundaries?.piers?.length) {
      const heightRows = boundaries.piers.flatMap(pier => Object.entries(pier.height_branches ?? {}).map(([name, h]) =>
        [pier.pier, name, decimals(h.reference_z_m), decimals(h.wall_height_mm), decimals(h.hw_over_lw),
          decimals(h.minimum_hcr_mm), limits(h.critical_interval_z_m), bool(h.ends_required)]));
      if (heightRows.length) tables['7.2'] = table(['Pier', 'Base scenario', 'Base (m)', 'Hw (mm)', 'Hw / lw',
        'Minimum Hcr (mm)', 'Critical elevation range (m)', 'End zones required'], heightRows,
        'Recorded base scenarios', 'Each row uses the same physical pier and its stated reference level.');
    }
    if (boundaries?.walls?.length) {
      const stacks = new Map((boundaries.piers ?? []).map(p => [p.pier, p]));
      const panels = new Map(piers.flatMap(p => (p.panel_details ?? []).map(row => [row.member, row])));
      tables['7.3'] = table(['Pier', 'Wall ID', 'Storey', 'End zone (mm)', 'Bars per end', 'End bar Ø (mm)',
        'Boundary tie Ø (mm)', 'Tie spacing (mm)', 'Web crosstie Ø (mm)', 'Web crossties', 'Minimum ties in 1 m²', 'Result or open input'],
        boundaries.walls.map(row => {
          const pier = stacks.get(row.pier), bars = pier?.adopted_constant_detail, ties = pier?.transverse_cage;
          const panel = panels.get(row.member_id), web = panel?.web_crossties;
          return [row.pier, row.member_id, row.story, bars?.end_width_mm, bars?.bars_per_end, bars?.diameter_mm,
            ties?.tie_diameter_mm, ties?.spacing_mm, web?.diameter_mm, web?.count, web?.minimum_ties_in_full_m2,
            row.reason || panel?.reason || (panel ? panel.status : row.cage_status || row.status)];
        }), boundaries.walls.length + ' physical wall panels', 'The proposed schedules keep the unassigned and held panels visible.');
    }
    if (!sections) return;
    const batch = sections.batch;
    if (batch?.rows?.length) {
      const counts = batch.counts;
      const overview = [], moments = [], combinations = [];
      const cause = r => r.reason || r.area_reason || r.material_reason || r.design.reason;
      for (const r of batch.rows) {
        const label = [r.pier || 'Unassigned', r.story, r.members.join(', ')];
        const design = r.design, assigned = r.assigned;
        overview.push([...label, percentage(assigned?.axial?.ratio), percentage(design.shear?.ratio),
          percentage(design.horizontal_joint?.ratio), percentage(design.pmm?.ratio), percentage(design.wall_beam?.ratio),
          design.scheduled_panels + '/' + design.panel_count, cause(r) || 'Conditional proposed design']);
        for (const [direction, m] of Object.entries(r.overturning)) {
          const ref = batch.overturning_storeys.find(x => x.story === r.story && x.direction === direction);
          moments.push([...label, decimals(r.native_bottom_z_m), direction, m.case, m.component, decimals(m.magnitude_knm, 3),
            decimals(m.uncertainty_knm, 5), m.combination_controls, decimals(ref?.storey_moment_knm, 2), ref?.project_reason]);
        }
        if (!Object.keys(r.overturning).length) moments.push([...label, null, null, null, null, null, null, null, null,
          r.overturning_reason || cause(r)]);
        for (const c of r.cuts) {
          const fr = c.reference_friction, web = c.reference_web;
          combinations.push([...label, c.combination, c.face, c.role, decimals(c.compression_kn, 2), percentage(c.axial_ratio),
            decimals(c.abs_v2_kn, 2), decimals(c.abs_v2_kn / 9.80665, 2), decimals(web?.vr_kn, 2),
            percentage(web?.source_v2_ratio), decimals(c.reference_plane_shear_kn, 2), decimals(fr?.resistance_kn, 2),
            percentage(fr?.upper_utilization), fr?.status, c.reason || r.area_reason || r.material_reason || c.force_basis]);
        }
      }
      const id = ['Pier', 'Storey', 'Wall IDs'];
      tables['7.0'] = table([...id, 'Net-area axial (%)', 'Design shear (%)', 'Design friction (%)', 'PMM (%)',
        'Wall–beam (%)', 'Scheduled panels', 'Design result or open input'], overview,
        coverage(counts.native_assigned_faces, counts.assigned_face_checks_expected, 'assigned face results'),
        'Each row covers the storey and wall IDs shown. Design columns use the proposed cage and its governing combination.',
        [['Physical walls', counts.physical_walls], ['Pier–storeys', counts.pier_storeys], ['Unassigned wall objects', counts.unassigned_walls],
         ['Assigned combinations', counts.assigned_combinations], ['Directional pier moments', counts.directional_moments]]);
      tables['7.7'] = table([...id, 'Bottom z (m)', 'Excitation', 'Case', 'Pier component', 'Centroid moment (kN·m)',
        'Rounding bound (kN·m)', 'Native equations', 'Total storey moment (kN·m)', 'Project share decision'], moments,
        coverage(counts.directional_moments, 2 * counts.pier_storeys, 'individual directional moments'),
        'Each scalar moment acts at its pier centroid. The building share requires the project base, the set of walls, coupling and a compatible total wall moment.');
      if (combinations.length) {
        tables['7.14'] = table([...id, 'Combination', 'Face', 'Load role', 'Compression (kN)', 'Net-area axial (%)',
          '|V2| (kN)', '|V2| (tf)', 'Web Vr (kN)', 'Web incl. strut (%)', 'Plane shear bound (kN)', 'Joint resistance (kN)',
          'Reference friction (%)', 'Joint check result', 'Source or open input'], combinations,
          counts.pier_storeys + ' pier–storeys', 'Native source cuts. Reference web uses two Ø12/200 curtains. The rough joint uses 0.75% anchored vertical steel, μ = 1 and both shear components.');
      }
    }
    const basement = sections.basement_coverage;
    if (basement && sections.basement_piers?.length) {
      const cuts = [], pressure = [], ends = [];
      for (const pier of sections.basement_piers) {
        const geo = pier.geometry, members = pier.members.join(', ');
        for (const r of pier.cuts) cuts.push([pier.pier, pier.story, members, r.face, r.combination, r.role,
          decimals(geo?.clear_web_area_m2, 3), limits(r.nd_kn), percentage(r.pmm_upper), r.reason || r.status]);
        if (!pier.cuts.length) cuts.push([pier.pier, pier.story, members, null, null, null, null, null, null, pier.reason || pier.status]);
        for (const id of pier.members) {
          const panel = geo?.panels.find(row => row.member === id), h = panel?.horizontal, v = panel?.vertical;
          const detail = [pier.pier, id, panel?.wall, decimals(panel?.span_m), decimals(panel?.clear_length_m)];
          for (const side of ['I', 'J']) {
            const e = panel?.pressure_connections?.ends?.[side], v = e?.transfer;
            ends.push([pier.pier, id, panel?.wall, side, e?.column, h?.diameter_mm, decimals(e?.position_i_mm, 1),
              decimals(e?.column_available_mm, 1), e?.specified_embedment_mm, v?.diameter_mm, decimals(v?.pitch_mm, 1),
              decimals(v?.peak_reaction_kn_m, 2), decimals(v?.resistance_kn_m, 2), percentage(v?.peak_ratio),
              e?.status || panel?.reason || pier.reason]);
          }
          if (h) {
            for (const r of h.cuts) pressure.push([...detail, r.combination, decimals(r.pressure_kn_m2, 2),
              decimals(r.moment_bound_knm_m, 2), percentage(r.moment_ratio), percentage(r.cracking_shear_ratio),
              h.diameter_mm, decimals(h.pitch_mm, 2), v?.diameter_mm, decimals(v?.pitch_mm, 2), v?.crossties,
              panel.reason || pier.status]);
          } else pressure.push([...detail, null, null, null, null, null, null, null, null, null, null,
            panel?.reason || pier.reason || pier.status]);
        }
      }
      tables['7.11'] = table(['Pier', 'Storey', 'Wall IDs', 'Pier end', 'Combination', 'Load scope', 'Net webs (m²)',
        'Compression interval (kN)', 'Maximum web PMM upper (%)', 'Result or open input'], cuts,
        coverage(basement.assigned_cuts_evaluated, basement.assigned_cuts_expected, 'assigned cuts across multi-panel piers'),
        'Each end uses the native pier origin. An equilibrium distribution allocates axial force and biaxial bending to the clear webs. Supporting column concrete and bars are reserved.');
      tables['7.12'] = table(['Pier', 'Wall ID', 'Wall', 'Column span (m)', 'Clear web (m)', 'Combination', 'Normal load (kN/m²)',
        'Bending bound (kN·m/m)', 'Bending (%)', 'Cracking shear (%)', 'Horizontal Ø (mm)', 'Horizontal pitch (mm)',
        'Vertical Ø (mm)', 'Vertical pitch (mm)', 'Crossties', 'Result or open input'], pressure,
        coverage(basement.scheduled_panels, basement.physical_panels, 'panels with proposed webs'),
        'Horizontal strips span between columns with zero relative transverse translation under the archived uniform pressure.');
      if (basement.physical_pressure_ends_expected !== undefined) tables['7.13'] = table(['Pier', 'Wall ID', 'Wall', 'End',
        'Support column', 'Web Ø (mm)', 'Required bond (mm)', 'Available (mm)', 'Proposed embedment (mm)', 'Dowel Ø (mm)',
        'Dowel pitch (mm)', 'Line reaction (kN/m)', 'Resistance (kN/m)', 'Utilization (%)', 'End result or open input'],
        ends, coverage(basement.physical_pressure_ends_satisfied, basement.physical_pressure_ends_expected, 'ends with a proposed pressure detail'),
        'Separate transverse dowels use μ = 0.6 at the vertical wall–column interface. End development uses the unfavourable bond position.');
    }
    const cuts = format => rowsFor('seismic_sections', row => [...cut(row), ...format(row)]);
    const shear = cuts(row => [decimals(row.ve_upper_kn, 2), percentage(row.shear_upper_ratio), status(row)]);
    if (shear.length) {
      tables['7.4'] = table([...headers, 'Heightwise Ve upper (kN)', 'Shear upper (%)', 'Section result or open input'],
        shear, coverage(sections.satisfied_height_shear, sections.expected_height_cuts, 'within shear bound'),
        basis + 'Heightwise Ve includes both base scenarios and the local face demand.');
    } else {
      const local = rowsFor('seismic_shear', row => [...cut(row), row.control_combination, percentage(row.upper_utilization), status(row)]);
      if (local.length) tables['7.4'] = table([...headers, 'Amplified control', 'Local shear upper (%)', 'Result or open input'],
        local, coverage(sections.satisfied_shear_bounds, sections.expected_shear_bounds, 'within local shear bound'),
        'Local shear at the recorded wall face and combination.');
    }
    const joints = rowsFor('construction_joints', row => [row.upper_member, row.story, decimals(row.z_m), row.combination,
      decimals(row.ve_in_plane_upper_kn, 2), decimals(row.available_friction_steel_mm2, 2), decimals(row.resistance_kn, 2),
      percentage(row.upper_utilization), status(row)]);
    if (joints.length) tables['7.5'] = table(['Pier', 'Upper wall ID', 'Storey', 'Elevation (m)', 'Combination',
      'Ve upper (kN)', 'Available steel (mm²)', 'Resistance (kN)', 'Friction upper (%)', 'Result or open input'],
      joints, coverage(sections.satisfied_joints, sections.expected_joints, 'within joint resistance'),
      'Each construction joint is counted once per combination. Resistance assumes ≥5 mm roughening and anchored bars across the joint.');
    const axial = cuts(row => [limits(row.nd_interval_kn), decimals(row.axial_limit_kn, 2), percentage(row.axial_ratio), status(row)]);
    if (axial.length) tables['7.6'] = table([...headers, 'Compression interval (kN)', '0.35 fck Ac (kN)',
      'Compression (%)', 'Section result or open input'], axial, coverage(sections.evaluated_axial, sections.expected_height_cuts, 'evaluated'),
      'Compression is positive. The combination shown supplies the axial interval.');
    const design = cuts(row => [decimals(row.z_m), limits(row.nd_interval_kn), decimals(row.m2_design_knm, 2),
      decimals(row.m3_design_knm, 2), percentage(row.pmm?.upper_utilization), row.chain_status,
      row.reason || (row.open_section_checks ?? []).join(', ')]);
    if (design.length) tables['7.8'] = table([...headers, 'Elevation (m)', 'Compression interval (kN)',
      'Design |M2| (kN·m)', 'Design |M3| (kN·m)', 'PMM upper (%)', 'Section design', 'Open checks'],
      design, coverage(sections.conditional_seismic_sections, sections.expected_height_cuts, 'conditional face designs'),
      basis + 'The PMM bound covers the entire axial interval and both moment signs. Each end retains its physical cut.');
    const connections = rowsFor('strong_wall_connections', row => [row.story, decimals(row.z_m), row.combination,
      (row.selected_beam_ends ?? []).map(end => end.beam + '/' + end.face).join(', '), decimals(row.mr_wall_lower_knm, 2),
      decimals(row.required_mr_knm, 2), percentage(row.upper_utilization), status(row)]);
    if (connections.length) tables['7.9'] = table(['Pier', 'Storey', 'Elevation (m)', 'Combination', 'Beam ID / end',
      'ΣMr wall lower (kN·m)', '1.2 × ΣMr beam upper (kN·m)', 'Demand / strength upper (%)', 'Result or open input'],
      connections, coverage(sections.satisfied_strong_wall, sections.expected_strong_wall, 'within moment strength'),
      'TBDY §7.6.6.2 applies Eq. 7.3 in the strong direction of a slender wall. Each row is one floor–pier connection and combination.');
    const gravity = rowsFor('gravity_rows', row => [...cut(row), decimals(row.compression_kn, 2), decimals(row.forces_kn_knm?.M2, 2),
      decimals(row.forces_kn_knm?.M3, 2), percentage(row.pmm_ratio), percentage(row.v2_over_vr), status(row)]);
    if (gravity.length) tables['7.10'] = table([...headers, 'Compression (kN)', 'M2 (kN·m)', 'M3 (kN·m)', 'PMM (%)',
      '|V2| / Vr (%)', 'Result or open input'], gravity, coverage(sections.evaluated_gravity, sections.expected_gravity, 'evaluated'),
      'Signed static forces use a common combination and physical face.');
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
    if (report.analysis_setup) {
      tables['1.6'] = analysisTable(report.analysis_setup);
      const rec = report.analysis_setup_reconciliation;
      if (rec) {
        const fam = rec.assigned_design_families;
        const stiff = rec.cracked_section_stiffness_audit;
        const noteBits = [];
        if (fam) noteBits.push(`Assigned families: ${(fam.bound_families || []).join(', ')} (remaining: ${(fam.remaining_unassigned_families || []).join(', ') || 'none'})`);
        if (stiff) noteBits.push(`TBDY Table 4.2 modifiers: ${stiff.status} (columns 0.70=${stiff.all_columns_match_0_70}, beams 0.35=${stiff.all_beams_match_0_35})`);
        if (noteBits.length) tables['1.6'].note = (tables['1.6'].note ? tables['1.6'].note + ' · ' : '') + noteBits.join(' · ');
      }
    }
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
      const scope = report.column_axial_expected_instances;
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
        axial.status, (scope?.dependency_blockers ?? axial.combination_plan.blockers).join(' · ') ||
          'TS 500 Eq. (7.7) numerical results for the captured combinations and stations. TBDY seismic applicability and project approval remain open.',
        [['Run combination source', sources[axial.combination_plan.source]],
          ['ETABS combinations in this run', axial.combination_plan.combinations.map(item => item.name).join(', ')],
          ['Completed columns', axial.completed_column_count + ' / ' + axial.expected_column_count],
          ['Evaluated column–combination pairs', scope
            ? scope.evaluated_count + ' / ' + scope.expected_count + (scope.scope_complete ? '' : ' · Scope incomplete')
            : axial.evaluated_member_combination_count + ' / ' + axial.expected_member_combination_count],
          ...(scope ? [['Unresolved expected pairs', scope.not_proven_count]] : []),
          ['Native rows', axial.native_force_row_count], ['Columns with observed exceedance', axial.observed_exceedance_count],
          ['Concrete factor γc', decimals(axial.gamma_c)]]);
    }
    const pmm = report.column_pmm;
    const pmmScope = report.column_pmm_expected_instances;
    const pmmMesh = pmmScope?.analysis_mesh;
    const cutLabel = cut => decimals(cut.object_station_m, 4) + ' m · ' +
      cut.analysis_element_id + ' · ' + decimals(cut.element_station_m, 4) + ' m';
    const cage = pmm?.section_evidence;
    const reinforcement = report.column_pmm_reinforcement;
    const minimum = reinforcement?.tbdy_longitudinal_minimum;
    const minimumRule = 'As ≥ 0.01 Ac';
    const minimumLabels = new Map([
      ['BELOW_MINIMUM', 'Does not satisfy ' + minimumRule],
      ['MEETS_MINIMUM', 'Satisfies ' + minimumRule],
    ]);
    const minimumAvailable = minimumLabels.has(minimum?.status) && minimum.formal_compliance === 'NOT_PROVEN' &&
      [minimum.minimum_percent, minimum.minimum_area_mm2, reinforcement.longitudinal_reinforcement_percent,
        reinforcement.longitudinal_steel_area_mm2, reinforcement.gross_section_area_mm2]
        .every(value => Number.isFinite(value) && value > 0);
    const minimumStatus = minimumAvailable ? minimumLabels.get(minimum.status) :
      cage ? 'Server data incomplete' : 'Section evidence unavailable';
    const minimumIssue = cage && !minimumAvailable
      ? 'The running server did not supply the minimum reinforcement results. Restart YENI with the same ETABS PID and reopen this run.'
      : null;
    const roles = {ETABS_CHECK_REINFORCEMENT: 'ETABS check reinforcement',
      ETABS_DESIGN_TEMPLATE: 'ETABS design template scenario'};
    const reinforcementBasis = roles[cage?.reinforcement_role] ?? cage?.reinforcement_role;
    const reinforcementHeaders = ['Bar count', 'Bar Ø (mm)', 'Total As (mm²)', 'Longitudinal steel (%)'];
    const reinforcementValues = [cage?.bar_count, decimals(cage?.longitudinal_bar_diameter_mm, 2),
      decimals(reinforcement?.longitudinal_steel_area_mm2, 2), decimals(reinforcement?.longitudinal_reinforcement_percent, 3)];
    const minimumHeaders = ['TBDY minimum (%)', 'Required As (mm²)', 'TBDY requirement · ' + minimumRule];
    const minimumValues = minimumAvailable
      ? [decimals(minimum.minimum_percent, 3), decimals(minimum.minimum_area_mm2, 2), minimumStatus]
      : ['Unavailable', 'Unavailable', minimumStatus];
    if (pmm) {
      const selection = report.r10_live?.engineer_column_selection;
      const candidate = selection?.member_id === pmm.member_id ? selection?.selected : null;
      const requiredCandidateArea = selection?.tbdy_minimum_longitudinal_area_mm2 ?? minimum?.minimum_area_mm2;
      const candidateInputs = candidate ? [
        ['Engine-selected candidate (approval pending)', candidate.label],
        ['Candidate As (mm²)', decimals(candidate.area_mm2, 2)],
        ['Candidate As / Ac (%)', decimals(candidate.rho_percent, 3)],
        ['TBDY required As (mm²) · ' + minimumRule, decimals(requiredCandidateArea, 2)],
        ...(selection.minimum_longitudinal_area_mm2 != null && selection.minimum_longitudinal_area_mm2 !== requiredCandidateArea
          ? [['Selection policy floor As (mm²)', decimals(selection.minimum_longitudinal_area_mm2, 2)]] : []),
      ] : [];
      if (minimumAvailable) {
        tables['4.2'] = table(
          ['ETABS Unique ID', 'Story', 'Section', 'Reinforcement basis', ...reinforcementHeaders,
            'Gross area (mm²)', ...minimumHeaders],
          [[pmm.member_id, pmm.story, pmm.section, reinforcementBasis, ...reinforcementValues,
            decimals(reinforcement.gross_section_area_mm2, 2), ...minimumValues]],
          minimumStatus, 'TBDY 2018 §7.3.2.1 requires ' + minimumRule + ' for column longitudinal reinforcement. This result applies to the recorded reinforcement basis.',
          [['Formal compliance', minimum.formal_compliance]]);
      }
      const stations = pmm.rows ?? [];
      const combinations = pmm.combinations ?? [];
      const completedCombinations = pmmScope?.numerically_complete_signed_pair_count ??
        combinations.filter(item => item.status === 'NUMERICAL_COMPLETE').length;
      const combinationGaps = combinations.filter(item => item.reason || !item.evaluated_station_count)
        .map(item => {
          const coverage = item.analysis_element_coverage;
          const missing = coverage?.missing_analysis_element_ids ?? [];
          const unmapped = coverage?.unmapped_analysis_element_ids ?? [];
          const cutCoverage = item.configured_cut_coverage;
          const missingCuts = cutCoverage?.missing_cuts ?? [];
          const ambiguousCuts = cutCoverage?.ambiguous_cuts ?? [];
          return {combination: item.name, status: item.status, reason: [item.reason,
            missing.length && ('Elements without forces: ' + missing.join(', ')),
            unmapped.length && ('Unmapped force elements: ' + unmapped.join(', ')),
            missingCuts.length && ('Missing configured cuts: ' + missingCuts.map(cutLabel).join(', ')),
            ambiguousCuts.length && ('Ambiguous configured cuts: ' + ambiguousCuts.map(cutLabel).join(', ')),
          ].filter(Boolean).join(' · ')};
        });
      const memberMesh = pmmMesh?.members?.[pmm.member_id];
      const requiredCuts = pmmScope?.configured_output_cuts?.[pmm.member_id];
      const rows = [...stations, ...combinationGaps].map(row => [
        pmm.member_id, pmm.story, pmm.section, row.combination, ...reinforcementValues, ...minimumValues, row.analysis_element_id,
        decimals(row.object_station_m), decimals(row.element_station_m), row.step_type, decimals(row.nd_kn),
        decimals(row.m2_knm), decimals(row.m3_knm), decimals(row.m2_design_knm), decimals(row.m3_design_knm),
        decimals(row.utilization), row.status, row.reason,
      ]);
      const critical = stations.reduce((best, row) =>
        row.utilization != null && (!best || row.utilization > best.utilization) ? row : best, null);
      tables['4.4'] = table(
        ['ETABS Unique ID', 'Story', 'Section', 'Combination', ...reinforcementHeaders, ...minimumHeaders,
          'Analysis element ID', 'Object station (m)', 'Element station (m)', 'Step', 'Nd (kN)',
          'M2 (kN·m)', 'M3 (kN·m)', 'M2 with eₘᵢₙ (kN·m)', 'M3 with eₘᵢₙ (kN·m)', 'Utilization', 'Status', 'Evidence gap'],
        rows, pmm.status, [minimumIssue, pmm.reason, 'Longitudinal steel percentage uses the ETABS bar areas used in this PMM scenario. Signed static vectors include TS 500 minimum eccentricity. Component envelopes supply independent extremes. Second-order design verification remains NOT_PROVEN.'].filter(Boolean).join(' '),
        [['Recorded column Unique ID', pmm.member_id], ['Story', pmm.story], ['Section', pmm.section],
          ['Largest resolved utilization', critical ? decimals(critical.utilization * 100, 2) + '%' : null],
          ['Combination and object station', critical ? critical.combination + ' · ' + decimals(critical.object_station_m, 2) + ' m' : null],
          ['Reinforcement basis', reinforcementBasis],
          ['TBDY minimum reinforcement', minimumAvailable ? decimals(minimum.minimum_percent, 3) + '% · ' + minimumStatus : minimumStatus],
          ...candidateInputs,
          ['Longitudinal bar count', cage?.bar_count], ['Longitudinal bar diameter (mm)', decimals(cage?.longitudinal_bar_diameter_mm)],
          ['Section t2 (mm)', decimals(cage?.t2_mm)], ['Section t3 (mm)', decimals(cage?.t3_mm)],
          ['Column–combination pairs with signed results', completedCombinations + ' / ' +
            (pmmScope?.expected_member_combination_count ?? combinations.length)],
          ...(pmmMesh ? [['Analysis mesh table', pmmMesh.mesh_table_status],
            ['Output station assignments', pmmMesh.station_table_status]] : []),
          ...(memberMesh?.roster_bound ? [['Expected analysis elements', memberMesh.expected_analysis_element_ids.join(', ')]] : []),
          ...(memberMesh?.station_assignment ? [
            ['ETABS output station rule', memberMesh.station_assignment.StationOpt],
            ...(memberMesh.station_assignment.StationOpt === 'Min Stations'
              ? [['ETABS minimum stations', memberMesh.station_assignment.MinStations]] : []),
          ] : []),
          ...(requiredCuts?.analysis_joint_native_coordinate_status ? [[
            'Native analysis joint coordinates', requiredCuts.analysis_joint_native_coordinate_status,
          ]] : []),
          ...(requiredCuts?.status === 'REQUIRED_SUBSET_BOUND' ? [[
            'Required ETABS cuts (object station · element ID · element station)', requiredCuts.cuts.map(cutLabel).join(', '),
          ]] : requiredCuts?.reason ? [['Configured cut evidence', requiredCuts.reason]] : []),
          ...(pmmScope && !pmmScope.independent_cut_census_proven
            ? [['Independent analysis cut inventory', 'Not verified']] : []),
          ['Scalar envelopes outside PMM', combinations.filter(item => item.status === 'OUT_OF_SCOPE').length],
          ['Evaluated stations', pmm.evaluated_station_count + ' / ' + pmm.expected_station_count],
          ['Stations with observed exceedance', pmm.observed_exceedance_count]]);
    }
    if (!pmm && pmmScope) {
      tables['4.4'] = table(['ETABS Unique ID', 'Combination', 'Status', 'Evidence gap'],
        pmmScope.instances.map(row => [row.element_id, row.combination, row.execution_status,
          [row.reason, pmmScope.configured_output_cuts?.[row.element_id]?.reason].filter(Boolean).join(' · ')]),
        'PMM blocked', pmmScope.dependency_blockers.join(' · '),
        [['Expected column–combination pairs', pmmScope.expected_member_combination_count]]);
    }
    const slenderness = report.column_slenderness_evidence;
    if (slenderness) {
      const geometry = slenderness.geometric_slenderness;
      const slendernessIssue = !Object.hasOwn(slenderness, 'geometric_slenderness')
        ? 'The running server did not supply the geometric slenderness projection. Restart YENI with the same ETABS PID and reopen this run.'
        : null;
      const rows = [2, 3].map(axis => [
        slenderness.member_id, slenderness.story, slenderness.section, ...reinforcementValues, ...minimumValues, axis,
        decimals(geometry?.['radius_local_' + axis + '_mm'], 2),
        decimals(geometry?.['frame_length_over_radius_local_' + axis], 2), 'NOT_PROVEN', 'NOT_PROVEN',
      ]);
      tables['4.5'] = table(
        ['ETABS Unique ID', 'Story', 'Section', ...reinforcementHeaders, ...minimumHeaders, 'Local axis', 'Gross section radius (mm)',
          'Geometric L / r', 'Effective slenderness', 'Moment magnification'],
        rows, slenderness.status,
        [minimumIssue, slendernessIssue, 'Geometric L / r uses the joint-to-joint ETABS frame length. Inputs pending verification include ' +
          slenderness.unverified_inputs.map(input => input.charAt(0).toLowerCase() + input.slice(1)).join(' · ') + '.'].filter(Boolean).join(' '), [
        ['ETABS Unique ID', slenderness.member_id], ['Story', slenderness.story], ['Section', slenderness.section],
        ['ETABS frame length (m)', decimals(slenderness.frame_length_m)],
        ['I-end joint Unique ID', slenderness.i_joint_id], ['J-end joint Unique ID', slenderness.j_joint_id],
        ['Observed force stations (m)', slenderness.observed_object_stations_m.map(value => decimals(value)).join(' / ') || null],
        ['Member force analysis order', slenderness.analysis_order],
        ['Global P–Δ precheck', slenderness.global_pdelta_status],
      ]);
    }
    const schedule = report.column_candidate_schedule;
    if (schedule?.rows?.length) {
      const candidates = schedule.rows;
      const identity = row => [row.member_id, row.story, row.section];
      const ids = ['ETABS Unique ID', 'Story', 'Section'];
      const state = 'Selected candidates · ' + schedule.bound_column_count + '/' + schedule.expected_column_count + ' bound';
      const note = 'Algorithm-selected candidates from this saved run; approval pending. '
        + 'The recorded ETABS template is a separate reinforcement basis. '
        + 'TBDY 2018 §7.3.2.1: As ≥ 0.01 Ac. Ties and crossties: §7.3.4.1–7.3.4.2.';
      const inputs = [['Expected columns', schedule.expected_column_count], ['Same-run cage bindings', schedule.bound_column_count],
        ['Reinforcement role', schedule.selection_role], ['Formal compliance', schedule.formal_compliance]];
      tables['4.2'] = table([...ids, 'Selected candidate', 'Bar count', 'Bar Ø (mm)', 'Selected As (mm²)',
        'As / Ac (%)', 'Minimum As (mm²)', 'Cover to tie (mm)', 'Clear bar spacing (mm)', 'Same-run cage binding', 'Selection status'],
        candidates.map(row => [...identity(row), row.label, row.bar_count, row.diameter_mm, decimals(row.area_mm2, 2),
          decimals(row.rho_percent, 3), decimals(row.minimum_area_mm2, 2), decimals(row.cover_to_tie_mm, 1),
          decimals(row.minimum_clear_spacing_mm, 1), row.binding_status, row.selection_status]), state, note, inputs);
      tables['4.6'] = table([...ids, 'Longitudinal candidate', 'Tie Ø (mm)', 'Confinement pitch (mm)', 'Midspan pitch (mm)',
        'Legs V2', 'Legs V3', 'Crossties V2', 'Crossties V3', 'Tied-bar spacing a (mm)', '25Ø limit (mm)',
        'Recorded transverse criteria met', 'Alerts', 'Same-run cage binding'],
        candidates.map(row => [...identity(row), row.label, row.tie_diameter_mm, row.confinement_spacing_mm,
          row.midspan_spacing_mm, row.legs_v2, row.legs_v3, row.crossties_parallel_v2, row.crossties_parallel_v3,
          decimals(row.crosstie_max_spacing_a_mm, 1), decimals(row.crosstie_limit_25_phi_mm, 1),
          bool(row.all_tbdy_checks_met), row.transverse_alerts.join(' · '), row.binding_status]), state,
        note + ' Hooks, anchorage, splice locations and physical confinement lengths require detailing verification.', inputs);
      tables['4.4'] = table([...ids, 'Selected candidate', 'Selected As (mm²)', 'As / Ac (%)', 'Minimum As (mm²)',
        'Static PMM utilization', 'Magnified reference PMM utilization', 'Spectral bound utilization',
        'Magnified PMM status', 'Spectral bound status', 'Same-run cage binding'],
        candidates.map(row => [...identity(row), row.label, decimals(row.area_mm2, 2), decimals(row.rho_percent, 3),
          decimals(row.minimum_area_mm2, 2), decimals(row.pmm_max_utilization, 4), decimals(row.magnified_pmm_utilization, 4),
          decimals(row.spectral_bound_utilization, 4), row.magnified_pmm_status, row.spectral_bound_status, row.binding_status]), state,
        note + ' Selected-cage static PMM includes minimum eccentricity. Magnification uses reference assumptions. '
          + 'Spectral corners bound independent extremes; they are not simultaneous force vectors.', inputs);
      tables['4.5'] = table([...ids, 'Selected candidate', 'Magnified reference PMM utilization',
        'Resolved rows', 'Expected rows', 'Magnified PMM status', 'Same-run cage binding'],
        candidates.map(row => [...identity(row), row.label, decimals(row.magnified_pmm_utilization, 4),
          row.magnified_pmm_resolved_rows, row.magnified_pmm_expected_rows, row.magnified_pmm_status, row.binding_status]), state,
        note + ' The same selected cage is used by the recorded R08 calculation. Physical clear length, effective length, '
          + 'sway classification, creep and analysis order remain subject to verification.', inputs);
    }
    if (wall?.items?.length) tables['7.1'] = table(['Story', 'ETABS Unique ID', 'Section', 'Panel length (m)', 'Thickness (mm)', 'Length/thickness', 'Status'],
      wall.items.map(row => [row.story, row.element_id, row.section, decimals(row.panel_length_m),
        decimals(row.thickness_mm), decimals(row.panel_length_thickness_ratio), row.status]),
      wall.status, 'These dimensions describe ETABS area panels. The complete physical wall or leg length requires verification.');
    const columnJoints = report.r10_live?.scwb_joints;
    if (columnJoints?.length) tables['4.8'] = table(['Column ID', 'End', 'Joint', 'Direction', 'Column IDs', 'Beam IDs',
      'Low axial decision', 'Governing interval combination', 'Strength / required lower bound', 'Column SCWB decision'],
      columnJoints.map(row => [row.target_member_id, row.target_end, row.joint_id, row.direction,
        (row.column_ids ?? []).join(', '), (row.beam_ids ?? []).join(', '), row.low_axial_exception?.status,
        row.seismic_axial_interval_check?.governing_combination, decimals(row.seismic_axial_interval_check?.minimum_ratio_lower),
        row.status]), columnJoints.length + ' column end–direction records',
      'TBDY §7.3.5. Each record identifies its target column end. Adjacent columns can share a physical joint. A sufficient lower ratio is at least 1.');
    addWallTables(tables, report.building_design);
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
      resultSha: report.design_stage_provenance?.snapshot_results_sha256,
      sourceLabel: fullCase(report.modal_case, report.source_mode === 'LIVE_ETABS' ? 'Saved live capture' : 'Saved source run'),
      reportUrl: sourceUrl('/report/print', runId), jsonUrl: sourceUrl('/api/export-checks', runId),
      analysisSetup: report.analysis_setup,
      analysisSetupReconciliation: report.analysis_setup_reconciliation,
      designAssignments: report.design_assignments,
      columnStrengthAvailable: report.source_mode === 'LIVE_ETABS' && report.analysis_setup?.definition_coverage_known === true,
      columnCandidates: (() => {
        const rows = (checkOf(report, 'column_rect_min')?.items ?? [])
          .filter(row => row.status !== 'NOT_APPLICABLE' && typeof row.element_id === 'string' && row.element_id)
          .map(row => [row.element_id, [row.element_id, row.story, row.section].filter(Boolean).join(' · ')]);
        return rows.length ? [['ALL', `ALL (${rows.length} columns · R15 building-wide)`], ...rows] : [];
      })(),
      columnPmmMember: report.column_pmm?.member_id,
      columnPmmReinforcement: report.column_pmm_reinforcement,
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
      error.code = body.code;
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
      info.textContent = message || 'Required ETABS units ' + requiredUnits;
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
      row.run_id, [row.pmm_member_id && 'PMM · Unique ID ' + row.pmm_member_id,
        row.model_name || 'ETABS archive', row.case,
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

  async function runLive(columnStrength = null, pmmMember = null) {
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
    const columnCheck = pmmMember ? 'column PMM' : 'axial compression';
    setRunStatus(columnStrength ? 'Reading the selected ETABS frame forces and checking ' + columnCheck + '…' :
      'Reading the locked ETABS model and evaluating the combined checks…');
    log('info', 'ETABS', (columnStrength ? 'Column force capture for ' + columnCheck + ' · ' : 'Combined live scan started · ') + modal);
    try {
      const wsState = workspace.getState();
      const query = new URLSearchParams();
      if (wsState?.assignments?.beamSelection) {
        query.set('beam_selection', JSON.stringify(wsState.assignments.beamSelection));
      }
      if (wsState?.assignments?.columnSelection) {
        query.set('column_selection', JSON.stringify(wsState.assignments.columnSelection));
      }
      if (columnStrength) {
        query.set('check', pmmMember ? 'column-pmm' : 'column-axial');
        if (pmmMember) query.set('member', pmmMember);
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
      if (columnStrength && (!body.column_axial || (pmmMember && !body.column_pmm && !body.column_axial_coverage))) {
        throw new Error('Restart the local YENI server to enable the column force check.');
      }
      if (pmmMember && body.column_pmm && body.column_pmm.member_id !== pmmMember) {
        throw new Error('The verified PMM run identifies a different ETABS column.');
      }
      const entry = {
        run_id: body.run_id, model_name: body.model_name, case: modal,
        captured_at_utc: new Date().toISOString(), source_mode: 'LIVE_ETABS',
        pmm_member_id: body.column_pmm?.member_id,
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
      if (body.column_pmm) {
        const pmm = body.column_pmm;
        log(pmm.evaluated_station_count ? 'info' : 'warn', 'COLUMN PMM',
          pmm.member_id + ' · ' + pmm.evaluated_station_count + '/' + pmm.expected_station_count + ' stations · ' + pmm.status);
      } else if (pmmMember) {
        const blockers = body.column_pmm_coverage?.dependency_blockers ?? body.column_axial_coverage?.dependency_blockers ?? [];
        log('warn', 'COLUMN PMM', ['Required PMM inputs unavailable', ...blockers].join(' · '));
      }
      const r03Blockers = body.analysis_setup_reconciliation?.reconciled_blocker_codes ?? body.analysis_setup?.blocker_codes;
      if (r03Blockers?.length) {
        log('warn', 'R03 ANALYSIS SETUP', r03Blockers.join(' · '));
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
      if (error.code === 'ETABS_CONNECTION_UNAVAILABLE') {
        showEtabsConnection(null, error.message);
      } else if (error.etabsSession) {
        showEtabsConnection(error.etabsSession);
      }
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
    const state = workspace.getState();
    if (state.selectedCheck === '4.4' && !state.pmmMember) return;
    runLive(state.assignments.columnStrength, state.selectedCheck === '4.4' ? state.pmmMember : null);
  });

  window.addEventListener('tbdy:apply-rebar-selection', async event => {
    if (busy) return;
    const {runId, beamSelection, columnSelection, wholeBuilding = false, allWalls = false, wallHingeStoreys} = event.detail ?? {};
    const statusEl = byId('deskRebarStatus');
    if (!runIdPattern.test(runId)) {
      if (statusEl) statusEl.textContent = 'Select a verified combined run before applying rebar settings.';
      return;
    }
    busy = true;
    requestVersion++;
    selector.disabled = true;
    byId('deskLive').disabled = true;
    probe.disabled = true;
    workspace.setLiveBusy(true);
    if (statusEl) statusEl.textContent = wholeBuilding ? 'Calculating the whole building…' : 'Re-evaluating selected run with engineer rebar & stirrup policies…';
    if (allWalls) byId('deskRunStatus').textContent = 'Calculating all piers, storeys and wall combinations…';
    try {
      const body = await json('/api/apply-rebar-selection', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          base_run_id: runId,
          ...(allWalls ? {} : {beam_selection: beamSelection, column_selection: columnSelection}),
          ...(wholeBuilding ? {whole_building: true} : {}),
          ...(allWalls ? {read_missing_wall_forces: true} : {}),
          ...(wholeBuilding && !allWalls && wallHingeStoreys ? {wall_hinge_aggregate_storeys: wallHingeStoreys} : {}),
        }),
      });
      const entry = {
        run_id: body.run_id, model_name: body.model_name, case: byId('deskModalCase').value.trim(),
        captured_at_utc: new Date().toISOString(), source_mode: 'LIVE_ETABS',
        pmm_member_id: body.column_pmm?.member_id,
      };
      entries = [entry, ...entries.filter(row => row.run_id !== entry.run_id)];
      renderPicker(entry.run_id);
      log('success', 'REBAR SELECTION', 'Applied engineer beam/column rebar policy → ' + entry.run_id);
      if (statusEl) {
        const building = body.building_design;
        const walls = building?.wall_sections;
        const wallCount = walls?.expected_height_cuts > 0
          ? ' Wall sections: ' + walls.conditional_seismic_sections + '/' + walls.expected_height_cuts + ' conditional face designs.' : '';
        statusEl.textContent = building
          ? (building.column_status_counts.conditional ?? 0) + ' of ' + building.column_count + ' column designs reached a conditional result.' + wallCount
          : 'Applied policy cleanly. Active run: ' + entry.run_id + ' (NOT_PROVEN).';
      }
      await activateSource(body.run_id);
      if (allWalls) {
        workspace.openCheck('7.0');
        const counts = body.building_design?.wall_sections?.batch?.counts;
        if (counts) byId('deskRunStatus').textContent = counts.physical_walls + ' physical walls · ' +
          counts.pier_storeys + ' pier–storeys · ' + counts.native_assigned_faces + '/' + counts.assigned_face_checks_expected + ' assigned face results';
      }
    } catch (error) {
      log('error', 'REBAR SELECTION', error.message);
      if (allWalls) byId('deskRunStatus').textContent = 'Wall calculation could not finish. ' + error.message;
      if (statusEl) statusEl.textContent = 'Rebar evaluation failed: ' + error.message;
    } finally {
      busy = false;
      selector.disabled = false;
      byId('deskLive').disabled = false;
      probe.disabled = false;
      workspace.setLiveBusy(false);
    }
  });

  async function start() {
    byId('deskLive').disabled = true;
    probe.disabled = true;
    try {
      const data = await json('/api/quick-history?view=summary');
      entries = Array.isArray(data.runs) ? data.runs.filter(entry => runIdPattern.test(entry.run_id)) : [];
      const pmmView = ['4.2', '4.4', '4.5'].includes(requestedCheck);
      const first = requestedRun === archivedColumn || runIdPattern.test(requestedRun)
        ? requestedRun
        : (pmmView ? entries.find(row => row.pmm_member_id)?.run_id : null) ?? entries[0]?.run_id;
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
