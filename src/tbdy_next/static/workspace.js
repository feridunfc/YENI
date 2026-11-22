/* Presentation of verified YENI results. Numerical checks are owned by the engine. */
(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  function node(tag, text, cls) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = String(text);
    if (cls) element.className = cls;
    return element;
  }
  const minimumLongitudinalReference = 'TBDY 2018 §7.3.2.1 · Minimum longitudinal reinforcement';
  const groups = [
    ['General and model setup', [
      ['1.0', 'Project information', 'Project and structural system', 'Source identity, materials and member sections', 0],
      ['1.1', 'Project and story geometry', 'CHK-001', 'Model geometry', 0],
      ['1.2', 'Concrete and reinforcing steel', 'Material sources', [
        'TBDY 2018 §7.2.5 · Concrete and reinforcing steel',
        'TBDY 2018 §7.1.3 · Concrete strength scope',
      ], 1],
      ['1.3', 'Sections and dimensions', 'Section sources', 'ETABS section definitions', 2],
      ['1.4', 'Section and material assignments', 'Model assignments', 'Member, section and material links', 3],
      ['1.5', 'Loads and mass source', 'Load and mass basis', 'TBDY 2018 §4.5.9 · Mass modeling', 4],
      ['1.6', 'Analysis cases and P–Δ settings', 'R03 · Analysis setup', [
        'TBDY 2018 §4.4.4 · Seismic load combinations',
        'TBDY 2018 §4.9.2 · Second-order effects',
      ], 5],
      ['1.7', 'Cracked-section stiffness', 'CHK-002', 'TBDY 2018 §4.5.8 and Table 4.2 · Effective section stiffness', 3]]],
    ['Seismic hazard and periods', [
      ['2.1', 'AFAD response spectrum', '§2.3', 'TBDY 2018 §§2.3–2.4 · Site coefficients and elastic design spectra', 6],
      ['2.2', 'Modal mass and periods', '§4.8', 'TBDY 2018 §4.8.1.2 · Modal participation and effective mass', 7],
      ['2.3', 'Base shear and β scaling', '§4.8.4', [
        'TBDY 2018 §4.7.1.1 · Eq. (4.19) · Equivalent base-shear lower bound',
        'TBDY 2018 §4.8.4.1 · Modal base-shear scaling',
      ], 8]]],
    ['Drift and irregularities', [
      ['3.1', 'Interstory drift', '§4.9.1', 'TBDY 2018 §4.9.1', 8],
      ['3.2', 'Global second order · θII', '§4.9.2', 'TBDY 2018 §4.9.2', 8],
      ['3.3', 'Irregularities · A1–A3 / B1–B3', '§3.6', 'TBDY 2018 §3.6 and Table 3.6 · Plan and vertical irregularities', 9]]],
    ['Column design', [
      ['4.1', 'Section dimensions', 'CHK-116', 'TBDY 2018 §7.3.1.1 · Minimum column section dimensions', 12],
      ['4.2', 'Longitudinal reinforcement ratio', 'CHK-117 / F03', minimumLongitudinalReference, 12],
      ['4.3', 'Axial compression limit', 'CHK-004 · CHK-005 / F01', [
        'TS 500 §7.4.1 · Eq. (7.7) · Column axial compression limit',
        'TBDY 2018 §7.3.1.2 · Seismic axial compression limit',
      ], 12],
      ['4.4', 'Biaxial PMM and minimum eccentricity', 'CHK-115 · CHK-119 / F02', [
        'TS 500 §6.3.10 · Eq. (6.16) · Minimum eccentricity',
        'TS 500 §7.5 · Axial compression and biaxial bending',
        minimumLongitudinalReference,
      ], 12],
      ['4.5', 'Slenderness and moment magnification', 'CHK-116–119 / β', [
        'TS 500 §§7.6.2.2–7.6.2.6 · Effective length, slenderness and moment magnification',
        'TBDY 2018 §4.9.2 · Global second-order effects',
        minimumLongitudinalReference,
      ], 12],
      ['4.6', 'Confinement, ties and crossties', 'CHK-123 / F07', 'TBDY 2018 §7.3.4.1', 12],
      ['4.7', 'Capacity design shear · Ve', 'CHK-126', 'TBDY 2018 §7.3.7', 12],
      ['4.8', 'Strong column–weak beam · SCWB', 'CHK-120', 'TBDY 2018 §7.3.5', 12]]],
    ['Beam design', [
      ['5.1', 'Section dimensions', '§7.4.1', 'TBDY 2018 §7.4.1.1(a)–(b) · Beam section dimensions', 11],
      ['5.2', 'Flexural reinforcement', '§7.4.2', 'TBDY 2018 §7.4.2', 11],
      ['5.3', 'Confinement ties', '§7.4.4', 'TBDY 2018 §7.4.4', 11],
      ['5.4', 'Capacity design shear · Ve', '§7.4.5', 'TBDY 2018 §7.4.5', 11]]],
    ['Beam–column joints', [
      ['6.1', 'Confined and unconfined joints', '§7.5', 'TBDY 2018 §7.5.1 · Joint confinement classification', 14],
      ['6.2', 'Joint shear · Ve', '§7.5', 'TBDY 2018 §7.5.2.1 · Eq. (7.11) · Joint shear demand', 14],
      ['6.3', 'Joint shear limit · Vmax', '§7.5', 'TBDY 2018 §7.5.2.2 · Eqs. (7.12)–(7.13) · Joint shear limits', 14]]],
    ['Shear walls and boundary elements', [
      ['7.1', 'Wall dimensions · Hw / lw', '§7.6.1', 'TBDY 2018 §7.6.1', 13],
      ['7.2', 'Critical wall height · Hcr', '§7.6.2', 'TBDY 2018 §7.6.2', 13],
      ['7.3', 'Boundary and web reinforcement', '§7.6', 'TBDY 2018 §§7.6.3–7.6.5 · Wall reinforcement', 13],
      ['7.4', 'Wall web shear · Ve', '§7.6', 'TBDY 2018 §§7.6.6.3 and 7.6.7.1 · Wall shear demand and strength', 13],
      ['7.5', 'Wall shear friction', 'Shear friction', 'TBDY 2018 §7.6.7.2 · Shear friction at wall construction joints', 13],
      ['7.6', 'Wall axial capacity', 'Axial capacity', 'TBDY 2018 §7.6.1.1 · Wall axial compression limit', 13],
      ['7.7', 'Wall overturning moment', 'Section cut · X / Y', 'TBDY 2018 §4.3.4.8 · Wall base overturning moments', 13],
      ['7.8', 'Seismic wall section design · PMM', 'Physical faces', 'TBDY 2018 §7.6.6.1 · Wall design moments', 13],
      ['7.9', 'Wall strong direction · Eq. 7.3', '§7.6.6.2', 'TBDY 2018 §7.6.6.2 · Floor moment strength in the strong direction of the wall', 13],
      ['7.10', 'Gravity wall section design', 'Signed forces', 'TS 500 · Section strength under axial force and bending', 13]]],
    ['Slabs and punching shear', [
      ['8.1', 'Column–slab punching shear', 'TS 500', 'TS 500 §8.3 · Punching shear strength and reinforcement', 10]]]
  ];
  const codePublications = [
    ['TBDY 2018', 'https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf'],
    ['TS 500', 'https://staff.emu.edu.tr/cemalgenes/Documents/courses/INSA471_2019_20_Bahar/TS500.pdf'],
  ];
  const regions = new Map();
  const strengthLabels = {
    ASSIGNED_DESIGN: 'Assigned design combinations', ETABS_STRENGTH: 'ETABS Strength selections',
    SAVED_DEFAULTS: 'Custom column selection',
  };
  const checks = new Map(groups.flatMap(([group, definitions]) => definitions.map(
    ([id, title, code, clause, legacy]) => [id, {id, title, code, references: [clause].flat(), legacy, group}]
  )));
  const irregularities = [
    ['A · Plan irregularities', [
      ['A1', 'Torsional irregularity', 'Story drift ratios in X and Y'],
      ['A2', 'Floor discontinuities', 'Slab openings, diaphragm and load transfer'],
      ['A3', 'Plan projections', 'Plan geometry and projection dimensions'],
    ]],
    ['B · Vertical irregularities', [
      ['B1', 'Weak story', 'Effective shear areas and infill assumptions'],
      ['B2', 'Soft story', 'Drift comparisons between adjacent stories'],
      ['B3', 'Discontinuity of vertical structural elements', 'Column and wall continuity and load transfer'],
    ]],
  ];
  const statusNames = {
    MEETS_SUBCONDITION: 'Meets criterion', DOES_NOT_MEET_SUBCONDITION: 'Outside limit',
    MEETS_NUMERICAL_CRITERION: 'Meets criterion', NOT_APPLICABLE: 'Out of scope',
    NOT_PROVEN: 'Evidence pending', SOURCE_NUMERICAL_CALCULATED: 'Calculated',
  };

  const BEAM_DIAMETERS = [12, 14, 16, 20, 22, 24, 25];
  const COLUMN_LONG_DIAMETERS = [14, 16, 20, 22, 24, 25];
  const TIE_DIAMETERS = [8, 10, 12];
  const defaultBeamSelection = () => ({
    top_continuous: {count: 2, diameter_mm: 12},
    bottom_continuous: {count: 2, diameter_mm: 14},
    allowed_additional_diameters_mm: [16, 20, 22, 24, 25],
    stirrup_confinement: {diameter_mm: 8, spacing_mm: 100, legs: 2},
    stirrup_span: {diameter_mm: 8, spacing_mm: 150, legs: 2},
    strictly_exceed_required: true,
  });
  const defaultColumnSelection = () => ({
    allowed_longitudinal_diameters_mm: [...COLUMN_LONG_DIAMETERS],
    tie_diameter_preference_mm: [...TIE_DIAMETERS],
    stirrup_confinement_spacing_mm: 100,
    stirrup_span_spacing_mm: 150,
    strictly_exceed_required: true,
  });
  const defaultSettings = () => ({
    assignmentVersion: 2, basement: false, level: 0,
    columnStrength: {source: null, defaults: null},
    assignments: {upper: {}, lower: {}},
    beamSelection: defaultBeamSelection(),
    columnSelection: defaultColumnSelection(),
  });
  const state = {
    selected: '1.0', view: 'check', settingsSection: 'general', region: 'gravity', scope: 'upper',
    bundle: null, settings: defaultSettings(), storageKey: null, pending: false, lastTable: null,
    spectrumName: null, liveBusy: false, forceColumn: '', forceCombination: '', pmmMember: '',
    pmmChoice: null,
  };
  const check = () => checks.get(state.selected);
  const isColumnForceCheck = id => id === '4.3' || id === '4.4';
  const tableFor = id => id === '1.0' ? state.bundle?.project?.table : state.bundle?.tables?.[id];
  const audit = () => state.bundle?.analysisSetup;
  const names = () => audit()?.defined_combination_names ?? [];
  const design = () => state.bundle?.designAssignments;
  const checkGroups = id => design()?.check_groups[id] ?? [];
  const assigned = (region, scope = state.scope) => state.settings.assignments[scope][region]
    ?? design()?.defaults[scope]?.[region] ?? [];
  const hasOverride = region => Object.hasOwn(state.settings.assignments[state.scope], region);
  const strengthNames = (strength = strengthSelection()) => strength.source === 'ETABS_STRENGTH'
    ? audit()?.strength_design_combinations ?? [] : strength.defaults;
  const emit = (type, detail) => window.dispatchEvent(new CustomEvent(type, {detail: structuredClone(detail)}));
  const fmt = (value, digits = 2) => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '—';
  let loadResult;
  let spectrumObserver;

  function strengthSelection() {
    const roles = checkGroups(isColumnForceCheck(state.selected) ? state.selected : '4.3');
    const groups = Object.fromEntries(roles.map(role => [role, assigned(role, 'upper')]));
    const assignedNames = [...new Set(Object.values(groups).flat())];
    const hasDefaults = roles.some(role => design().defaults.upper[role]?.length);
    const source = state.settings.columnStrength.source ?? (hasDefaults || assignedNames.length
      ? 'ASSIGNED_DESIGN' : 'ETABS_STRENGTH');
    return {
      source, groups,
      defaults: source === 'SAVED_DEFAULTS' ? state.settings.columnStrength.defaults ?? assignedNames : assignedNames,
    };
  }

  function workingSettings() {
    return {...state.settings, columnStrength: strengthSelection(),
      assignments: Object.fromEntries(['upper', 'lower'].map(scope => [scope,
        Object.fromEntries([...regions.keys()].map(region => [region, assigned(region, scope)]))]))};
  }

  function buildNavigation() {
    const tree = byId('deskCheckTree');
    const select = node('select');
    select.id = 'deskMobileCheck';
    for (const [group, definitions] of groups) {
      const detail = node('details', undefined, 'check-group');
      detail.dataset.checkGroup = group;
      detail.append(node('summary', group));
      const items = node('div', undefined, 'desk-check-items');
      const optgroup = node('optgroup');
      optgroup.label = group;
      for (const [id, title, code] of definitions) {
        const button = node('button', undefined, 'desk-check-item');
        button.type = 'button';
        button.dataset.deskCheck = id;
        const label = node('span', title);
        label.append(node('small', code));
        const signal = node('span', undefined, 'check-indicator');
        signal.setAttribute('aria-hidden', 'true');
        button.append(node('span', id), label, signal);
        items.append(button);
        const option = node('option', id + ' · ' + title);
        option.value = id;
        optgroup.append(option);
      }
      detail.append(items);
      tree.append(detail);
      select.append(optgroup);
    }
    const mobile = node('label', undefined, 'desk-mobile-picker');
    mobile.append(node('span', 'Selected check'), select);
    byId('deskRunStatus').after(mobile);
    select.addEventListener('change', () => selectCheck(select.value));
  }

  function selectCheck(id) {
    if (!checks.has(id)) return;
    state.selected = id;
    state.view = 'check';
    document.querySelectorAll('.check-group').forEach(group => {
      group.open = group.dataset.checkGroup === check().group;
    });
    render();
  }

  function openSettings(section = 'general') {
    state.view = 'settings';
    state.settingsSection = ['general', 'combos', 'rebar'].includes(section) ? section : 'general';
    render();
  }

  function inspector(panel) {
    for (const name of ['Console', 'Section', 'Combos']) {
      byId('inspectorTab' + name).setAttribute('aria-selected', String(name === panel));
      byId('inspector' + name).hidden = name !== panel;
    }
  }

  function openSource(tab) {
    emit('tbdy:open-source', {legacyTab: tab, checkId: state.selected, runId: state.bundle?.runId});
  }

  function initSettings() {
    const identity = state.bundle?.modelKey;
    const key = identity ? 'tbdy-workspace-combos-v1:' + identity : null;
    if (key && key === state.storageKey) return;
    state.settings = defaultSettings();
    state.storageKey = key;
    state.scope = 'upper';
    if (!key) return;

    let saved;
    try {
      saved = JSON.parse(localStorage.getItem(key));
    } catch {
      return;
    }
    for (const scope of ['upper', 'lower']) {
      for (const id of regions.keys()) {
        const values = saved?.assignments?.[scope]?.[id];
        // The old UI saved untouched groups as empty arrays. Start them with the current defaults.
        if (Array.isArray(values) && (saved.assignmentVersion === 2 || values.length)) {
          state.settings.assignments[scope][id] = [...new Set(values.filter(name => typeof name === 'string'))].sort();
        }
      }
    }
    state.settings.basement = saved?.basement === true;
    if (Number.isFinite(saved?.level)) state.settings.level = saved.level;
    const strength = saved?.columnStrength;
    if (Array.isArray(strength?.defaults) && (saved.assignmentVersion === 2 || strength.defaults.length)) {
      state.settings.columnStrength.defaults = [...new Set(strength.defaults.filter(name => typeof name === 'string'))];
    }
    if (Object.hasOwn(strengthLabels, strength?.source)) {
      state.settings.columnStrength.source = strength.source === 'SAVED_DEFAULTS' && state.settings.columnStrength.defaults === null
        ? 'ASSIGNED_DESIGN' : strength.source;
    }
    const filterDiams = (raw, allowed, preserveOrder = false) => {
      if (!Array.isArray(raw)) return null;
      const valid = raw.filter(d => Number.isInteger(d) && allowed.includes(d));
      if (!valid.length) return null;
      return preserveOrder ? [...new Set(valid)] : [...new Set(valid)].sort((a, b) => a - b);
    };
    const bs = saved?.beamSelection;
    if (bs && typeof bs === 'object') {
      const defB = state.settings.beamSelection;
      for (const face of ['top_continuous', 'bottom_continuous']) {
        if (Number.isInteger(bs[face]?.count) && bs[face].count >= 2) defB[face].count = bs[face].count;
        if (BEAM_DIAMETERS.includes(bs[face]?.diameter_mm)) defB[face].diameter_mm = bs[face].diameter_mm;
      }
      defB.allowed_additional_diameters_mm = filterDiams(bs.allowed_additional_diameters_mm, BEAM_DIAMETERS)
        ?? defB.allowed_additional_diameters_mm;
      for (const zone of ['stirrup_confinement', 'stirrup_span']) {
        if (TIE_DIAMETERS.includes(bs[zone]?.diameter_mm)) defB[zone].diameter_mm = bs[zone].diameter_mm;
        if (Number.isFinite(bs[zone]?.spacing_mm) && bs[zone].spacing_mm > 0) defB[zone].spacing_mm = bs[zone].spacing_mm;
        if (Number.isInteger(bs[zone]?.legs) && bs[zone].legs >= 2 && bs[zone].legs <= 6) defB[zone].legs = bs[zone].legs;
      }
      if (typeof bs.strictly_exceed_required === 'boolean') defB.strictly_exceed_required = bs.strictly_exceed_required;
    }
    const cs = saved?.columnSelection;
    if (cs && typeof cs === 'object') {
      const defC = state.settings.columnSelection;
      defC.allowed_longitudinal_diameters_mm = filterDiams(cs.allowed_longitudinal_diameters_mm, COLUMN_LONG_DIAMETERS)
        ?? defC.allowed_longitudinal_diameters_mm;
      defC.tie_diameter_preference_mm = filterDiams(cs.tie_diameter_preference_mm, TIE_DIAMETERS, true)
        ?? defC.tie_diameter_preference_mm;
      if (Number.isFinite(cs.stirrup_confinement_spacing_mm) && cs.stirrup_confinement_spacing_mm > 0) {
        defC.stirrup_confinement_spacing_mm = cs.stirrup_confinement_spacing_mm;
      }
      if (Number.isFinite(cs.stirrup_span_spacing_mm) && cs.stirrup_span_spacing_mm > 0) {
        defC.stirrup_span_spacing_mm = cs.stirrup_span_spacing_mm;
      }
    }
  }

  function persistSettings() {
    if (!state.storageKey) return;
    const note = byId('deskAssignmentNote');
    try {
      localStorage.setItem(state.storageKey, JSON.stringify(state.settings));
      note.textContent = 'Project settings saved in this browser.';
    } catch {
      note.textContent = 'Browser storage is unavailable. This draft is available for the current session.';
    }
    emit('tbdy:assignments-change', {modelKey: state.bundle.modelKey, settings: workingSettings()});
  }

  function badge(text, kind = '') {
    return node('span', text, 'desk-badge ' + kind);
  }

  function renderCombos() {
    const active = byId('deskActiveCombos');
    active.replaceChildren();
    if (isColumnForceCheck(check().id) && state.bundle?.columnStrengthAvailable) {
      const strength = strengthSelection();
      const options = strengthNames(strength);
      const basis = strengthLabels[strength.source];
      active.append(badge(basis + ' · ' + options.length + ' combinations'));
      for (const name of options) active.append(badge(name));
    } else {
      const combinations = new Set();
      for (const id of checkGroups(check().id)) {
        const values = assigned(id);
        const tag = badge(regions.get(id) + ' · ' + values.length + ' assigned');
        tag.title = values.join(', ');
        active.append(tag);
        for (const name of values) combinations.add(name);
      }
      for (const name of combinations) active.append(badge(name));
    }
    const summary = byId('deskComboSummary');
    summary.replaceChildren(node('p', state.scope === 'upper' ? 'Superstructure draft' : 'Substructure draft', 'desk-label'));
    for (const [id, title] of regions) {
      const row = node('div', undefined, 'rail-kv');
      row.append(node('span', title), node('strong', assigned(id).length));
      summary.append(row);
    }
  }

  function drawTable(host, table) {
    const t = node('table', undefined, 'desk-table');
    const head = node('thead'), header = node('tr');
    for (const text of table.headers) {
      const th = node('th', text);
      th.scope = 'col';
      header.append(th);
    }
    head.append(header);
    t.append(head);
    const body = node('tbody');
    for (const row of table.rows) {
      const line = node('tr');
      row.forEach((value, index) => {
        const text = value ?? '—';
        const cell = node('td');
        if (table.headers[index] === 'ETABS Unique IDs by story') cell.className = 'member-list';
        if ((index === row.length - 1 || table.headers[index].startsWith('fck ')) &&
            /^(PASS|FAIL|NOT_PROVEN|UNAVAILABLE|NOT_APPLICABLE|PROPOSED|SOURCE_|MEETS_|DOES_NOT_MEET)/.test(text)) {
          const label = String(text);
          const style = /^(PASS|MEETS_)/.test(label) ? 'success' : /^(FAIL|DOES_NOT_MEET)/.test(label) ? 'danger' : 'warning';
          const tag = badge(statusNames[label] ?? label, style);
          tag.title = label;
          cell.classList.add('status-cell');
          cell.append(tag);
        } else {
          cell.textContent = text;
          if (/^-?\d+(\.\d+)?(?:e[+-]?\d+)?$/i.test(text)) cell.className = 'numeric';
        }
        line.append(cell);
      });
      body.append(line);
    }
    t.append(body);
    host.replaceChildren(t);
  }

  function renderIrregularities(host) {
    host.replaceChildren();
    const results = state.bundle?.irregularities ?? {};
    for (const [title, items] of irregularities) {
      const section = node('section', undefined, 'irregularity-group');
      section.append(node('h3', title));
      for (const [code, title, description] of items) {
        const row = node('div', undefined, 'irregularity-row'), text = node('div');
        text.append(node('strong', code + ' · ' + title), node('p', description));
        const result = results[code];
        row.append(text, badge(result?.status || 'Evidence pending', 'warning'));
        const action = node('button', 'View source rows', 'desk-button');
        action.type = 'button';
        action.disabled = !result?.rows?.length;
        action.addEventListener('click', () => {
          emit('tbdy:open-irregularity', {code, checkId: '3.3'});
          const expanded = action.getAttribute('aria-expanded') === 'true';
          action.setAttribute('aria-expanded', String(!expanded));
          detail.hidden = expanded;
        });
        action.setAttribute('aria-expanded', 'false');
        const detailId = 'irregularity-' + code;
        action.setAttribute('aria-controls', detailId);
        row.append(action);
        const detail = node('div', undefined, 'desk-table-wrap');
        detail.id = detailId;
        detail.hidden = true;
        if (result?.rows?.length) {
          drawTable(detail, result);
          detail.append(node('p', result.note, 'desk-result-note'));
        }
        section.append(row, detail);
      }
      host.append(section);
    }
  }

  function fieldGroups(host, groups) {
    host.replaceChildren();
    for (const [title, fields] of groups) {
      const group = node('section', undefined, 'desk-field-group');
      const values = node('div', undefined, 'desk-fields');
      for (const [name, value] of fields) {
        const label = node('label', undefined, 'desk-field');
        const input = node('input');
        input.readOnly = true;
        input.value = value ?? 'Unavailable';
        input.toggleAttribute('data-unavailable', value == null);
        label.append(node('span', name), input);
        values.append(label);
      }
      group.append(node('h3', title), values);
      host.append(group);
    }
  }

  function referenceCard(host, title) {
    const card = node('section', undefined, 'desk-card');
    card.append(node('h2', title));
    host.append(card);
    return card;
  }

  function renderProjectInformation() {
    const side = byId('deskReferenceFields'), content = byId('deskReferenceContent');
    const project = state.bundle?.project;
    const fallback = [['Project identification', [['ETABS model', state.bundle?.modelName],
      ['Latitude (°)', null], ['Longitude (°)', null]]]];
    fieldGroups(side, project?.groups ?? fallback);
    content.replaceChildren();
    const card = referenceCard(content, 'Structural system summary');
    if (!project?.table.rows.length) {
      card.append(node('p', 'A verified model capture is required for the structural inventory.'));
      return;
    }
    const summary = node('p', project.facts.map(([label, value]) => label + ' · ' + (value ?? 'Unavailable')).join('   |   '), 'desk-label');
    const frame = node('div', undefined, 'desk-table-wrap');
    drawTable(frame, project.table);
    card.append(summary, frame, node('p', project.table.note, 'desk-result-note'));
  }

  function drawSpectrum(canvas, points) {
    const width = canvas.clientWidth, height = canvas.clientHeight;
    if (width <= 0 || height <= 0) return;
    const scale = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    const ctx = canvas.getContext('2d');
    ctx.scale(scale, scale);
    ctx.font = '11px system-ui, sans-serif';
    const left = 43, top = 12, right = width - 12, bottom = height - 36;
    const maxX = points.at(-1)[0];
    const maxY = points.reduce((maximum, point) => Math.max(maximum, point[1]), 0);
    const x = period => left + (right - left) * period / maxX;
    const y = value => bottom - (bottom - top) * value / maxY;
    const tick = value => value.toLocaleString('en-GB', {maximumSignificantDigits: 3, useGrouping: false});
    ctx.strokeStyle = '#dce4ed';
    ctx.fillStyle = '#52687f';
    for (let index = 0; index <= 4; index++) {
      const fraction = index / 4;
      const horizontal = top + (bottom - top) * fraction;
      const vertical = left + (right - left) * fraction;
      ctx.beginPath();
      ctx.moveTo(left, horizontal); ctx.lineTo(right, horizontal);
      ctx.moveTo(vertical, top); ctx.lineTo(vertical, bottom);
      ctx.stroke();
      ctx.textAlign = 'right';
      ctx.fillText(tick(maxY * (1 - fraction)), left - 5, horizontal + 4);
      ctx.textAlign = 'center';
      ctx.fillText(tick(maxX * fraction), vertical, bottom + 15);
    }
    ctx.fillText('Period (s)', (left + right) / 2, height - 4);
    ctx.beginPath();
    points.forEach(([period, value], index) => index ? ctx.lineTo(x(period), y(value)) : ctx.moveTo(x(period), y(value)));
    ctx.strokeStyle = '#25628e';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = '#25628e';
    for (const [period, value] of points) {
      ctx.beginPath();
      ctx.arc(x(period), y(value), 2, 0, 2 * Math.PI);
      ctx.fill();
    }
  }

  function renderSeismicInformation() {
    const side = byId('deskReferenceFields'), content = byId('deskReferenceContent');
    const seismic = state.bundle?.seismic;
    const series = seismic?.functions ?? [];
    const item = series.find(functionData => functionData.name === state.spectrumName) ?? series[0];
    const params = item?.parameters ?? {};
    const corners = seismic?.cornerPeriods;
    const fieldNumber = value => Number.isFinite(Number(value)) && value != null
      ? Number(value).toLocaleString('en-GB', {maximumFractionDigits: 5, useGrouping: false}) : value;
    fieldGroups(side, [
      ['Site and hazard', [['Latitude (°)', null], ['Longitude (°)', null], ['Site class', params.SiteClass],
        ['Ground-motion level', null], ['PGA (g)', null], ['PGV (cm/s)', null]]],
      ['ETABS function parameters', [['Function', item?.name], ['Direction', params.Direction],
        ['R', params.R], ['D', params.D], ['Importance factor I', params.I],
        ['Live load mass factor n', null], ['Ss', params.Ss], ['S1', params.S1],
        ['Fs', params.Fs], ['F1', params.F1], ['SDS', params.SDS], ['SD1', params.SD1],
        ['Tₐ (s)', fieldNumber(corners?.T_A)], ['Tᵦ (s)', fieldNumber(corners?.T_B)], ['TL (s)', params.TL],
        ['Building height class', null], ['Building use class', null], ['Seismic design class', null]]],
    ]);
    content.replaceChildren();
    const card = referenceCard(content, 'Captured response spectrum');
    if (!item) {
      card.append(node('p', 'The verified source has no captured response spectrum function.'));
      return;
    }
    if (series.length > 1) {
      const label = node('label', undefined, 'desk-field');
      const selector = node('select');
      for (const {name} of series) {
        const option = node('option', name);
        option.value = name;
        selector.append(option);
      }
      selector.value = item.name;
      selector.addEventListener('change', () => {
        spectrumObserver?.disconnect();
        state.spectrumName = selector.value;
        renderSeismicInformation();
        byId('deskExcel').disabled = !state.lastTable || state.pending;
      });
      label.append(node('span', 'Captured function'), selector);
      card.append(label);
    }
    if (item.points.length >= 2 && item.points.at(-1)[0] > 0 && item.points.some(point => point[1] > 0)) {
      const figure = node('figure', undefined, 'desk-spectrum');
      const caption = node('figcaption', item.name + ' · ETABS ordinate (dimensionless)');
      const canvas = node('canvas');
      canvas.setAttribute('role', 'img');
      canvas.setAttribute('aria-label', 'ETABS response spectrum source points. A table of the values follows.');
      figure.append(caption, canvas);
      card.append(figure);
      drawSpectrum(canvas, item.points);
      spectrumObserver = new ResizeObserver(() => drawSpectrum(canvas, item.points));
      spectrumObserver.observe(canvas);
    }
    if (item.cases.length) {
      const caseTable = node('div', undefined, 'desk-table-wrap');
      drawTable(caseTable, {headers: ['Case', 'Load direction', 'Modal case', 'ETABS scale (m/s²)', 'Eccentricity ratio'],
        rows: item.cases.map(row => [row.Name, row.LoadName, row.ModalCase, row.TransAccSF, row.EccenRatio])});
      card.append(caseTable);
    }
    const raw = tableFor('2.1');
    const exactRows = raw?.rows.filter(row => row[0] === item.name) ?? [];
    state.lastTable = exactRows.length ? {...raw, rows: exactRows} : null;
    if (exactRows.length) {
      const details = node('details');
      const host = node('div', undefined, 'desk-table-wrap');
      drawTable(host, {...raw, rows: exactRows});
      details.append(node('summary', exactRows.length + ' captured spectrum points'), host);
      card.append(details);
    }
    card.append(node('p', 'Source ordinates and load-case settings come from the selected ETABS capture. The ground-motion level and AFAD site input require separate evidence.', 'desk-result-note'));
    if (!series.some(functionData => functionData.parameters.Direction === 'Vertical')) {
      const vertical = referenceCard(content, 'Vertical response spectrum');
      vertical.append(node('p', 'No vertical spectrum function was captured for this source.', 'desk-label'));
    }
  }

  function renderResult() {
    const current = check(), table = tableFor(current.id);
    const p0 = state.bundle?.p0_gate_report;
    const host = byId('deskResultTable'), inputs = byId('deskInputs');
    inputs.replaceChildren();
    const reference = current.id === '1.0' || current.id === '2.1';
    const fields = reference ? [] : table?.inputs ?? [];
    byId('deskInputCard').hidden = fields.length === 0;
    for (const [label, value] of fields) {
      const field = node('label', undefined, 'desk-field'), input = node('input');
      input.readOnly = true;
      input.value = value ?? '—';
      input.title = input.value;
      field.append(node('span', label), input);
      inputs.append(field);
    }
    state.lastTable = table?.rows?.length ? table : null;
    byId('deskReferenceView').hidden = !reference;
    byId('deskResultsCard').hidden = reference;
    const pmmResults = current.id === '4.4';
    const slendernessResults = current.id === '4.5';
    byId('deskResultsTitle').textContent = pmmResults ? '4.4 · PMM check results' :
      slendernessResults ? '4.5 · Slenderness results' : current.id === '4.2' ? '4.2 · Longitudinal reinforcement results' : 'Check results';
    host.classList.toggle('column-results-table',
      ['4.2', '4.4', '4.5'].includes(current.id) && Boolean(state.bundle?.columnPmmMember));
    renderPmmReinforcement();
    spectrumObserver?.disconnect();
    spectrumObserver = null;
    if (reference) {
      host.replaceChildren();
      if (current.id === '1.0') renderProjectInformation();
      else renderSeismicInformation();
    }
    byId('deskExcel').disabled = !state.lastTable || state.pending;
    const runColumn = byId('deskReadColumnForces');
    const columnForceCheck = isColumnForceCheck(current.id) && !p0;
    const pmm = current.id === '4.4' && !p0;
    byId('deskViewPmmResults').hidden = current.id !== '4.4' || !state.lastTable;
    const pmmPicker = byId('deskPmmPicker'), pmmSelect = byId('deskPmmMember');
    const pmmChoices = state.bundle?.columnCandidates ?? [];
    pmmPicker.hidden = !pmm;
    if (pmm) {
      state.pmmMember = setOptions(pmmSelect, [['', 'Select an ETABS Unique ID'], ...pmmChoices], state.pmmMember);
      pmmSelect.disabled = !state.bundle?.columnStrengthAvailable || !pmmChoices.length || state.liveBusy;
    }
    runColumn.hidden = !columnForceCheck;
    const combos = strengthNames();
    const missingCombos = combos.filter(name => !names().includes(name));
    let forceStatus = '';
    if (state.liveBusy) {
      forceStatus = 'Wait for the current ETABS operation to finish.';
    } else if (state.pending) {
      forceStatus = 'Verifying the saved source…';
    } else if (!state.bundle?.columnStrengthAvailable) {
      forceStatus = 'Select a live ETABS run with verified combination definitions.';
    } else if (pmm && !pmmChoices.length) {
      forceStatus = 'This run has no column Unique IDs available for PMM.';
    } else if (pmm && !state.pmmMember) {
      forceStatus = 'Choose an ETABS Unique ID above to enable Read forces and check.';
    } else if (!combos.length) {
      forceStatus = 'Assign combinations for this check in Edit assignments.';
    } else if (missingCombos.length) {
      forceStatus = 'Update the assignments. Missing from this run: ' + missingCombos.join(', ');
    }
    runColumn.disabled = !columnForceCheck || Boolean(forceStatus);
    const forceStatusLabel = byId('deskColumnForceStatus');
    forceStatusLabel.textContent = columnForceCheck ? forceStatus : '';
    forceStatusLabel.hidden = !columnForceCheck || !forceStatus;
    byId('deskQuickResult').classList.toggle('primary', runColumn.hidden);
    byId('deskQuickResult').disabled = !state.bundle || state.pending;
    byId('deskQuickResult').textContent = state.pending ? 'Verifying saved source…' : 'Replay saved run';
    byId('deskTableScope').textContent = p0 ? p0.member + ' / ' + p0.label :
      state.bundle?.runId ? 'Run ' + state.bundle.runId.slice(-8) : '';
    byId('deskResultNote').textContent = table?.note || '';
    const references = current.references.map(text => [
      text, codePublications.find(([standard]) => text.startsWith(standard))?.[1],
    ]);
    byId('deskCheckReferenceTitle').textContent = references.some(([, href]) => href) ? 'Code references' : 'Source basis';
    byId('deskCheckReferenceList').replaceChildren(...references.map(([text, href]) => {
      const item = node('li');
      if (href) {
        const link = node('a', text);
        link.href = href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        item.append(link);
      } else {
        item.textContent = text;
      }
      return item;
    }));
    renderNativeForces();
    if (reference) return;
    if (current.id === '3.3') {
      renderIrregularities(host);
    } else if (table?.rows?.length) {
      drawTable(host, table);
    } else {
      const box = node('div', undefined, 'desk-empty');
      if (current.id === '4.2' || slendernessResults) {
        const savedPmm = state.bundle?.columnPmmMember;
        const evidence = slendernessResults ? 'column slenderness evidence' : 'longitudinal reinforcement evidence';
        let message = 'Select a saved PMM run to show ' + evidence + '.';
        if (savedPmm) {
          message = slendernessResults || state.bundle.columnPmmReinforcement
            ? 'Restart the local YENI server with the same ETABS PID to display ' + evidence + '.'
            : 'Verified longitudinal reinforcement is unavailable for this PMM run.';
        }
        box.append(node('strong', message));
        if (!savedPmm && state.bundle?.columnStrengthAvailable && state.bundle.runId) {
          const link = node('a', 'Open 4.4 PMM', 'desk-button');
          link.href = '/?' + new URLSearchParams({run: state.bundle.runId, check: '4.4'});
          box.append(link);
        }
        host.replaceChildren(box);
        return;
      }
      const prompt = pmm && state.bundle
        ? 'PMM result unavailable for this run.'
        : columnForceCheck
          ? (state.bundle?.columnStrengthAvailable
              ? 'Read forces for the selected column strength combinations.'
              : 'Select a live run with an ETABS combination catalog.')
          : (state.bundle ? 'Verified result unavailable for this check' : 'Select a verified source run');
      box.append(node('strong', prompt));
      if (state.bundle?.runId && !columnForceCheck) {
        const button = node('button', 'Open legacy source & analysis ↗', 'desk-button');
        button.type = 'button';
        button.addEventListener('click', () => openSource(current.legacy));
        box.append(button);
      }
      host.replaceChildren(box);
    }
  }

  function setOptions(select, choices, selected) {
    select.replaceChildren(...choices.map(([value, label]) => {
      const option = node('option', label);
      option.value = value;
      return option;
    }));
    select.value = choices.some(([value]) => value === selected) ? selected : choices[0]?.[0] ?? '';
    return select.value;
  }

  function renderPmmReinforcement() {
    const panel = byId('deskPmmReinforcement');
    const cage = state.bundle?.columnPmmReinforcement;
    panel.hidden = check().id !== '4.4' || !cage;
    if (panel.hidden) return;

    const size = value => value == null ? '—' : String(Number(value.toFixed(2)));
    const basis = cage.reinforcement_role === 'ETABS_DESIGN_TEMPLATE' ? 'ETABS design template scenario' : 'ETABS check reinforcement';
    byId('deskPmmReinforcementScope').textContent = 'Unique ID ' + state.bundle.columnPmmMember + ' · ' + basis;
    const fields = [
      ['Local 2 × local 3 (mm)', size(cage.t2_mm) + ' × ' + size(cage.t3_mm)],
      ['Longitudinal bars', cage.bar_count + ' × Ø' + size(cage.longitudinal_bar_diameter_mm)],
      ['Bars per face (local 2 / local 3)', cage.bars_per_face_2 + ' / ' + cage.bars_per_face_3],
      ['Recorded area per bar (mm²)', size(cage.longitudinal_bar_area_mm2)],
      ['Longitudinal bar material', cage.steel_material_name],
      ['Cover to outer tie (mm)', size(cage.cover_to_tie_mm)],
      ['Tie diameter (mm)', size(cage.tie_diameter_mm)], ['Tie spacing along local 1 (mm)', size(cage.tie_spacing_mm)],
      ['Tie bars parallel to local 2 / local 3', size(cage.tie_bars_parallel_2) + ' / ' + size(cage.tie_bars_parallel_3)],
      ['Tie material', cage.tie_material_name],
    ];
    byId('deskPmmReinforcementValues').replaceChildren(...fields.map(([label, value]) => {
      const row = node('div');
      row.append(node('dt', label), node('dd', value || '—'));
      return row;
    }));
    drawPmmSection(byId('deskPmmSection'), cage);
  }

  function drawPmmSection(canvas, cage) {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const scale = Math.min((canvas.width - 76) / cage.t2_mm, (canvas.height - 64) / cage.t3_mm);
    const w = cage.t2_mm * scale, h = cage.t3_mm * scale;
    const cx = canvas.width / 2, cy = (canvas.height - 20) / 2;
    const x = cx - w / 2, y = cy - h / 2;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#f0f4f8';
    ctx.strokeStyle = '#546c84';
    ctx.lineWidth = 1;
    ctx.fillRect(x, y, w, h);
    ctx.strokeRect(x, y, w, h);
    const inset = (cage.cover_to_tie_mm + cage.tie_diameter_mm / 2) * scale;
    ctx.strokeStyle = '#2d779f';
    ctx.lineWidth = cage.tie_diameter_mm * scale;
    ctx.strokeRect(x + inset, y + inset, w - 2 * inset, h - 2 * inset);
    ctx.fillStyle = '#25638b';
    for (const [local2, local3] of cage.bar_positions_mm) {
      ctx.beginPath();
      ctx.arc(cx + local2 * scale, cy - local3 * scale, cage.longitudinal_bar_diameter_mm * scale / 2, 0, 2 * Math.PI);
      ctx.fill();
    }
    ctx.fillStyle = '#50687e';
    ctx.font = '12px system-ui';
    ctx.textAlign = 'center';
    ctx.fillText('Local 2', cx, y + h + 21);
    ctx.save();
    ctx.translate(x - 15, cy);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Local 3', 0, 0);
    ctx.restore();
  }

  function renderNativeForces() {
    const panel = byId('deskNativeForces');
    const source = state.bundle?.columnForces;
    const pmm = check().id === '4.4';
    const members = Object.keys(source?.rowsets ?? {}).filter(member => !pmm || member === state.bundle.columnPmmMember);
    panel.hidden = !isColumnForceCheck(check().id) || !members.length;
    if (panel.hidden) return;
    const picker = byId('deskForceColumn');
    const column = setOptions(picker, members.map(member => [member, member]), state.forceColumn);
    picker.disabled = pmm;
    if (!pmm) state.forceColumn = column;
    const data = source.rowsets[column];
    const combos = [...new Set(data.LoadCase)].sort();
    state.forceCombination = setOptions(byId('deskForceCombination'), combos.map(name => [name, name]),
      state.forceCombination);
    const meaning = source.combinations.find(entry => entry.name === state.forceCombination)?.force_semantics;
    const forceTypes = {
      STATIC_SIGNED_VECTOR: 'Signed static rows',
      SCALAR_COMPONENT_ENVELOPE: 'Component envelope',
    };
    byId('deskForceSemantics').textContent = (forceTypes[meaning] ?? 'Native component output') + ' · Local axes';
    const fields = ['Obj', 'ObjSta', 'Elm', 'ElmSta', 'LoadCase', 'StepType', 'StepNum',
      'P', 'V2', 'V3', 'T', 'M2', 'M3'];
    const headers = ['ETABS Unique ID', 'Object station (m)', 'Analysis element ID', 'Element station (m)', 'Combination', 'Step',
      'Step number', 'P (kN)', 'V2 (kN)', 'V3 (kN)', 'T (kN·m)', 'M2 (kN·m)', 'M3 (kN·m)'];
    const rows = data.LoadCase.flatMap((name, index) => name === state.forceCombination
      ? [fields.map(field => typeof data[field][index] === 'number' ? fmt(data[field][index], 4) : data[field][index])]
      : []);
    drawTable(byId('deskForceResult'), {headers, rows});
  }

  function refreshComboButtons() {
    byId('deskAddCombo').disabled = !state.storageKey || !byId('deskAvailable').selectedOptions.length;
    byId('deskRemoveCombo').disabled = !state.storageKey || !byId('deskAssigned').selectedOptions.length;
    byId('deskResetRegion').disabled = !state.storageKey || !hasOverride(state.region);
  }

  function renderSettings() {
    byId('deskGeneralCheck').disabled = state.pending || !state.bundle;
    byId('deskF04Check').disabled = state.pending || !state.bundle;
    byId('deskGeneralAuditStatus').textContent = state.bundle
      ? 'Source evidence for the selected run. Formal compliance is NOT_PROVEN.'
      : 'Select a verified source to inspect model evidence.';
    const general = byId('deskGeneralAuditTable');
    const list = node('div', undefined, 'desk-table');
    for (const current of checks.values()) {
      if (!current.id.startsWith('1.') || current.id === '1.0') continue;
      const row = node('div', undefined, 'rail-kv');
      const button = node('button', current.title + ' ↗', 'desk-matrix-select');
      button.type = 'button';
      button.dataset.deskCheck = current.id;
      const status = tableFor(current.id)?.status ?? 'Evidence pending';
      row.append(button, badge(status, 'warning'));
      list.append(row);
    }
    general.replaceChildren(list);
    const stiffness = byId('deskStiffnessEvidence');
    stiffness.textContent = tableFor('1.7')?.note ||
      'Section definitions, effective object modifiers and analysis use each require source evidence.';

    byId('deskBasement').checked = state.settings.basement;
    byId('deskBasement').disabled = !state.storageKey;
    byId('deskBasementLevel').value = state.settings.level;
    byId('deskBasementLevel').disabled = !state.storageKey || !state.settings.basement;
    byId('deskComboScope').value = state.scope;
    byId('deskComboScope').disabled = !state.storageKey || !state.settings.basement;
    const strength = strengthSelection();
    const available = Boolean(state.bundle?.columnStrengthAvailable);
    byId('deskStrengthSource').value = strength.source;
    byId('deskStrengthSource').querySelector('[value="ASSIGNED_DESIGN"]').disabled = !design();
    byId('deskStrengthSource').disabled = !available || state.liveBusy;
    byId('deskStrengthDefaultsField').hidden = strength.source !== 'SAVED_DEFAULTS';
    byId('deskResetStrength').hidden = strength.source !== 'SAVED_DEFAULTS' || state.settings.columnStrength.defaults === null;
    byId('deskResetStrength').disabled = !available || state.liveBusy;
    const defaults = byId('deskStrengthDefaults');
    const known = new Set(names());
    defaults.replaceChildren(...[...new Set([...names(), ...strength.defaults])].map(name => {
      const option = node('option', known.has(name) ? name : name + ' (missing from source)');
      option.value = name;
      option.selected = strength.defaults.includes(name);
      return option;
    }));
    defaults.disabled = !available || state.liveBusy;
    const selectedNames = strengthNames(strength);
    const missing = selectedNames.filter(name => !known.has(name));
    let summary = selectedNames.join(' · ') || 'Select model combinations for this check.';
    if (strength.source === 'ASSIGNED_DESIGN') {
      summary = Object.entries(strength.groups).map(([role, combos]) =>
        regions.get(role) + ' (' + combos.length + ') · ' + (combos.join(', ') || 'No assigned combinations')).join('\n');
    }
    byId('deskStrengthSummary').textContent = !available ? 'Select a live run with verified combination definitions.'
      : missing.length ? 'Missing from the selected source: ' + missing.join(', ') : summary;
    byId('deskRegionTitle').textContent = regions.get(state.region) ?? 'Select a design group';
    byId('deskModelComboTitle').textContent = 'Model combinations (' + names().length + ')';
    const matrix = node('div', undefined, 'desk-combo-controls');
    for (const [id, title] of regions) {
      const row = node('div', undefined, 'rail-kv');
      const button = node('button', title, 'desk-matrix-select');
      button.type = 'button';
      button.dataset.comboRegion = id;
      button.setAttribute('aria-pressed', String(state.region === id));
      const count = assigned(id).length;
      row.append(button, badge(count + ' assigned', state.region === id ? 'success' : ''));
      matrix.append(row);
    }
    byId('deskComboMatrix').replaceChildren(matrix);
    const currentAssignments = new Set(assigned(state.region));
    const unassignedNames = regions.has(state.region) ? names().filter(name => !currentAssignments.has(name)) : [];
    for (const [id, choices] of [['deskAvailable', unassignedNames], ['deskAssigned', [...currentAssignments]]]) {
      const select = byId(id);
      select.replaceChildren();
      for (const name of choices) {
        const option = node('option', known.has(name) ? name : name + ' (missing from source)');
        option.value = name;
        select.append(option);
      }
    }
    const references = byId('deskComboReferences');
    references.replaceChildren();
    for (const [label, combinations] of [['ETABS result envelopes', design()?.envelopes],
        ['Combinations without a project default', design()?.unassigned_combinations]]) {
      if (!combinations?.length) continue;
      const details = node('details');
      details.append(node('summary', label + ' (' + combinations.length + ')'), node('p', combinations.join(' · ')));
      references.append(details);
    }
    refreshComboButtons();
  }

  function renderDiameterCheckboxes(hostId, choices, selectedList, disabled, onUpdate) {
    const host = byId(hostId);
    if (!host) return;
    host.replaceChildren(...choices.map(diam => {
      const label = node('label', undefined, 'desk-checkbox');
      const box = node('input');
      box.type = 'checkbox';
      box.value = String(diam);
      box.checked = selectedList.includes(diam);
      box.disabled = disabled || (box.checked && selectedList.length <= 1);
      box.addEventListener('change', () => {
        const next = box.checked
          ? [...new Set([...selectedList, diam])]
          : selectedList.filter(d => d !== diam);
        if (next.length) onUpdate(next);
      });
      label.append(box, ' Φ' + diam);
      return label;
    }));
  }

  function renderRebarSettings() {
    const bs = state.settings.beamSelection;
    const cs = state.settings.columnSelection;
    const disabled = state.liveBusy || state.pending;
    if (!byId('deskBeamTopContDia')) return;
    byId('deskBeamTopContDia').value = String(bs.top_continuous.diameter_mm);
    byId('deskBeamTopContDia').disabled = disabled;
    byId('deskBeamTopContCount').value = bs.top_continuous.count;
    byId('deskBeamTopContCount').disabled = disabled;
    byId('deskBeamBotContDia').value = String(bs.bottom_continuous.diameter_mm);
    byId('deskBeamBotContDia').disabled = disabled;
    byId('deskBeamBotContCount').value = bs.bottom_continuous.count;
    byId('deskBeamBotContCount').disabled = disabled;
    byId('deskBeamConfDia').value = String(bs.stirrup_confinement.diameter_mm);
    byId('deskBeamConfDia').disabled = disabled;
    byId('deskBeamConfSpacing').value = bs.stirrup_confinement.spacing_mm;
    byId('deskBeamConfSpacing').disabled = disabled;
    if (byId('deskBeamConfLegs')) {
      byId('deskBeamConfLegs').value = String(bs.stirrup_confinement.legs ?? 2);
      byId('deskBeamConfLegs').disabled = disabled;
    }
    byId('deskBeamSpanDia').value = String(bs.stirrup_span.diameter_mm);
    byId('deskBeamSpanDia').disabled = disabled;
    byId('deskBeamSpanSpacing').value = bs.stirrup_span.spacing_mm;
    byId('deskBeamSpanSpacing').disabled = disabled;
    if (byId('deskBeamSpanLegs')) {
      byId('deskBeamSpanLegs').value = String(bs.stirrup_span.legs ?? 2);
      byId('deskBeamSpanLegs').disabled = disabled;
    }
    byId('deskBeamStrictOver').checked = Boolean(bs.strictly_exceed_required);
    byId('deskBeamStrictOver').disabled = disabled;
    byId('deskColConfSpacing').value = cs.stirrup_confinement_spacing_mm;
    byId('deskColConfSpacing').disabled = disabled;
    byId('deskColSpanSpacing').value = cs.stirrup_span_spacing_mm;
    byId('deskColSpanSpacing').disabled = disabled;
    if (byId('deskTightenStirrups')) byId('deskTightenStirrups').disabled = disabled;
    byId('deskResetRebar').disabled = disabled;
    byId('deskApplyRebar').disabled = disabled || !state.bundle?.runId || state.bundle?.runId === 'column-127';
    byId('deskRunBuilding').disabled = byId('deskApplyRebar').disabled || state.bundle?.columnPmmMember !== 'ALL';
    byId('deskBuildingHingeStoreys').disabled = byId('deskRunBuilding').disabled;
    renderDiameterCheckboxes('deskBeamAllowedDiams', BEAM_DIAMETERS, bs.allowed_additional_diameters_mm, disabled, next => {
      bs.allowed_additional_diameters_mm = next.sort((a, b) => a - b);
      persistSettings();
      render();
    });
    renderDiameterCheckboxes('deskColLongDiams', COLUMN_LONG_DIAMETERS, cs.allowed_longitudinal_diameters_mm, disabled, next => {
      cs.allowed_longitudinal_diameters_mm = next.sort((a, b) => a - b);
      persistSettings();
      render();
    });
    renderDiameterCheckboxes('deskColTieDiams', TIE_DIAMETERS, cs.tie_diameter_preference_mm, disabled, next => {
      cs.tie_diameter_preference_mm = next.sort((a, b) => a - b);
      persistSettings();
      render();
    });
  }

  function renderAudit() {
    const data = audit();
    byId('f04Badge').textContent = state.bundle?.p0_gate_report ? 'F04' : 'R03';
    const detailText = state.bundle?.p0_gate_report ? 'F04 · Archived column analysis setup' : 'R03 · Analysis and design setup';
    for (const id of ['deskF04Result', 'deskInspectorF04']) {
      const host = byId(id);
      host.replaceChildren(node('strong', detailText));
      if (!data) {
        host.append(node('p', 'Verified analysis setup is unavailable for this source.'));
        continue;
      }
      host.append(node('div', data.defined_combination_names.length + ' combination definitions observed.'),
        node('div', data.design_selection_observed
          ? data.design_selection_count + ' recorded design selections.'
          : 'ETABS design selection table unavailable.'),
        node('div', 'Analysis generation · ' + (data.analysis_generation_proven ? 'Verified' : 'NOT_PROVEN')));
      const strength = data.strength_design_combinations;
      if (strength?.length) {
        const details = node('details');
        details.append(node('summary', 'ETABS Strength selections (' + strength.length + ')'),
          node('div', strength.join(' · '), 'audit-detail'));
        host.append(details);
      }
      if (data.blocker_codes?.length) {
        const details = node('details'), list = node('ul');
        for (const reason of data.blocker_codes) list.append(node('li', reason));
        details.append(node('summary', 'Open evidence'), list);
        host.append(details);
      }
    }
  }

  function renderSection() {
    const host = byId('deskSectionDrawing'), summary = byId('deskRebarSummary');
    const info = state.bundle?.reconciled?.r08?.geometry;
    const p0 = state.bundle?.p0_gate_report;
    host.replaceChildren();
    summary.replaceChildren();
    const source = byId('runSummaryTree');
    source.replaceChildren(...[
      state.bundle?.modelName,
      state.bundle?.runId,
      state.bundle?.sourceSha ? 'SHA-256 ' + state.bundle.sourceSha : null,
      state.bundle?.resultSha ? 'Results SHA-256 ' + state.bundle.resultSha : null,
      state.bundle?.reconciled?.case,
    ].filter(Boolean).map(text => node('li', text)));
    byId('deskSectionTitle').textContent = p0 ? 'Section · ' + p0.member + ' / ' + p0.label : 'Section';
    if (!info || !p0) {
      summary.append(node('p', 'Select the archived column receipt for its section and reinforcement evidence.', 'desk-label'));
      return;
    }
    const ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 260 260');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', p0.section_name + ' schematic section and proposed reinforcement');
    svg.classList.add('section-svg');
    const add = (tag, attrs, text) => {
      const element = document.createElementNS(ns, tag);
      for (const [name, value] of Object.entries(attrs)) element.setAttribute(name, value);
      if (text) element.textContent = text;
      svg.append(element);
    };
    const cage = p0.p0b_gates.f03_reinforcement_states.proposed_scenario_16phi24;
    const {local2_extent_mm: width, local3_extent_mm: depth} = p0.local_dims_mm;
    const scale = 170 / Math.max(width, depth), w = width * scale, h = depth * scale;
    const left = (260 - w) / 2, top = (260 - h) / 2;
    add('rect', {x: left, y: top, width: w, height: h, class: 'concrete'});
    const perSide = cage.bar_count / 4, inset = 10;
    for (let i = 0; i < cage.bar_count; i++) {
      const t = (i % perSide) / perSide, side = Math.floor(i / perSide);
      const points = [[t, 0], [1, t], [1 - t, 1], [0, 1 - t]];
      add('circle', {
        cx: left + inset + points[side][0] * (w - 2 * inset),
        cy: top + inset + points[side][1] * (h - 2 * inset), r: 4, class: 'bar',
      });
    }
    add('text', {x: 130, y: 20, 'text-anchor': 'middle'}, fmt(width, 0) + ' × ' + fmt(depth, 0) + ' mm');
    add('text', {x: 130, y: 246, 'text-anchor': 'middle'}, 'Proposed layout · schematic');
    host.append(svg);
    for (const r of Object.values(p0.p0b_gates.f03_reinforcement_states).filter(row => ['TEMPLATE', 'PROPOSED'].includes(row.role))) {
      const box = node('div', undefined, 'reinforcement-role');
      box.append(node('strong', r.role + ' · ' + r.bar_count + 'Φ' + fmt(r.bar_diameter_mm, 0)),
        node('span', 'ρ = ' + fmt(r.rho * 100, 3) + '% · ' +
          (r.would_fail_if_selected ? 'Fails area check if selected' : 'Engineering approval pending')));
      summary.append(box);
    }
  }

  function render() {
    const current = check(), settings = state.view === 'settings';
    const section = state.settingsSection;
    byId('deskWorkspaceShell').classList.toggle('wide-results', !settings &&
      (['4.2', '4.4', '4.5', '4.8'].includes(current.id) || current.id.startsWith('7.')));
    byId('deskCheckView').hidden = settings;
    byId('deskSettingsView').hidden = !settings;
    byId('deskGeneralSettings').hidden = section !== 'general';
    byId('deskComboSettings').hidden = section !== 'combos';
    byId('deskRebarSettings').hidden = section !== 'rebar';
    byId('settingsGeneralTab').setAttribute('aria-selected', String(section === 'general'));
    byId('settingsCombosTab').setAttribute('aria-selected', String(section === 'combos'));
    byId('settingsRebarTab').setAttribute('aria-selected', String(section === 'rebar'));
    byId('deskTitle').textContent = settings ? 'Settings' : current.id + ' · ' + current.title;
    byId('deskCheckState').textContent = settings ? '' : tableFor(current.id)?.status ??
      (state.bundle ? 'Evidence pending' : 'Source pending');
    byId('deskCheckState').hidden = settings;
    byId('deskCheckCode').textContent = settings ? '' : current.code;
    byId('deskBreadcrumb').textContent = settings ? 'Settings' : current.group;
    byId('deskContextFocus').textContent = state.bundle?.p0_gate_report ? 'Archived column' : 'Model scope';
    const hasCombos = checkGroups(current.id).length > 0 || (isColumnForceCheck(current.id) && state.bundle?.columnStrengthAvailable);
    byId('deskActiveCombos').closest('.desk-combo-strip').hidden = settings || !hasCombos || !state.storageKey;
    byId('deskMobileCheck').value = current.id;
    document.querySelectorAll('#deskCheckTree [data-desk-check]').forEach(button => {
      const id = button.dataset.deskCheck;
      button.setAttribute('aria-current', String(!settings && id === state.selected));
      const available = tableFor(id)?.rows?.length;
      button.querySelector('.check-indicator').classList.toggle('review', Boolean(available));
    });
    renderCombos();
    renderResult();
    renderSettings();
    renderRebarSettings();
    renderAudit();
  }

  function setData(input) {
    if (input && (!input.tables || !input.modelName)) throw new TypeError('WORKSPACE_RESULT_REQUIRED');
    if (input?.runId !== state.bundle?.runId) byId('deskBuildingHingeStoreys').value = '';
    state.bundle = input;
    const choice = state.pmmChoice;
    const rememberedMember = choice && input?.modelKey === choice.modelKey
      && input.columnCandidates?.some(([id]) => id === choice.memberId) ? choice.memberId : '';
    state.pmmMember = input?.columnPmmMember ?? rememberedMember;
    regions.clear();
    for (const group of design()?.groups ?? []) regions.set(group.id, group.title);
    if (input && !regions.has(state.region)) state.region = regions.keys().next().value ?? 'gravity';
    if (!input?.seismic?.functions?.some(item => item.name === state.spectrumName)) state.spectrumName = null;
    initSettings();
    byId('deskAssignmentNote').textContent = input && !design()
      ? 'Restart the local YENI server to load the engine design assignments.' : '';
    const p0 = input?.p0_gate_report;
    byId('deskModel').textContent = input?.modelName || 'No model selected';
    byId('deskFocus').textContent = p0 ? 'Unique ID ' + p0.member + ' · ETABS label ' + p0.label + ' · Story ' + p0.story :
      input?.runId ? 'Run ' + input.runId.slice(-8) : '';
    byId('deskSourceState').textContent = input?.sourceLabel ?? 'Source pending';
    for (const [id, url] of [['deskReport', input?.reportUrl], ['deskJson', input?.jsonUrl]]) {
      const link = byId(id);
      link.hidden = !url;
      if (url) link.href = url;
      else link.removeAttribute('href');
    }
    renderSection();
    render();
  }

  async function replay(withAudit = false) {
    if (!loadResult || !state.bundle || state.pending) return;
    const detail = {checkId: state.selected, settings: workingSettings(), audit: withAudit};
    const selected = state.bundle;
    emit(withAudit ? 'tbdy:request-audit' : 'tbdy:request-calculation', detail);
    state.pending = true;
    render();
    const status = byId('deskLoadStatus');
    status.textContent = 'Verifying the saved source…';
    try {
      const next = await loadResult(structuredClone(detail));
      if (state.bundle !== selected) return;
      setData(next);
      status.textContent = 'Saved source and results verified.';
      window.engineConsole.log('info', 'REPLAY', 'Verified ' + next.sourceLabel + '.');
    } catch (error) {
      if (state.bundle !== selected) return;
      setData(null);
      status.textContent = 'Could not verify the saved source. ' + error.message;
      window.engineConsole.log('error', 'REPLAY', error.message);
    } finally {
      state.pending = false;
      render();
    }
  }

  function editCombos(add) {
    const select = byId(add ? 'deskAvailable' : 'deskAssigned');
    const selected = new Set([...select.selectedOptions].map(option => option.value));
    const previous = assigned(state.region);
    state.settings.assignments[state.scope][state.region] = add
      ? [...new Set([...previous, ...selected])].sort()
      : previous.filter(name => !selected.has(name));
    persistSettings();
    render();
  }
  function xlsx(rows) {
    // Minimal OOXML, ZIP STORE, inline strings (never formulas or executable cells).
    const sheet = rows.map((row, r) => '<row r="' + (r + 1) + '">' + row.map((cell, c) =>
      '<c r="' + String.fromCharCode(65 + c) + (r + 1) + '" t="inlineStr"><is><t xml:space="preserve">' + xml(cell) + '</t></is></c>').join('') + '</row>').join('');
    const files = [
      ['[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'],
      ['_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'],
      ['xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Check" sheetId="1" r:id="rId1"/></sheets></workbook>'],
      ['xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'],
      ['xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + sheet + '</sheetData></worksheet>']
    ];
    const encoder = new TextEncoder(), localParts = [], centralParts = [];
    let offset = 0, centralSize = 0;
    for (const [path, value] of files) {
      const name = encoder.encode(path), bytes = encoder.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + value);
      let crc = 0xffffffff;
      for (const byte of bytes) {crc ^= byte; for (let j = 0; j < 8; j++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);}
      crc = (crc ^ 0xffffffff) >>> 0;
      const local = new Uint8Array(30 + name.length), a = new DataView(local.buffer);
      a.setUint32(0, 0x04034b50, true); a.setUint16(4, 20, true); a.setUint16(12, 33, true);
      a.setUint32(14, crc, true); a.setUint32(18, bytes.length, true); a.setUint32(22, bytes.length, true);
      a.setUint16(26, name.length, true); local.set(name, 30);
      const central = new Uint8Array(46 + name.length), b = new DataView(central.buffer);
      b.setUint32(0, 0x02014b50, true); b.setUint16(4, 20, true); b.setUint16(6, 20, true); b.setUint16(14, 33, true);
      b.setUint32(16, crc, true); b.setUint32(20, bytes.length, true); b.setUint32(24, bytes.length, true);
      b.setUint16(28, name.length, true); b.setUint32(42, offset, true); central.set(name, 46);
      localParts.push(local, bytes); centralParts.push(central);
      offset += local.length + bytes.length; centralSize += central.length;
    }
    const end = new Uint8Array(22), e = new DataView(end.buffer);
    e.setUint32(0, 0x06054b50, true); e.setUint16(8, files.length, true); e.setUint16(10, files.length, true);
    e.setUint32(12, centralSize, true); e.setUint32(16, offset, true);
    return new Blob([...localParts, ...centralParts, end], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
  }
  function xml(value) {
    return String(value ?? '').replace(/[<>&"']/g, character =>
      ({'<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;'}[character]));
  }

  function exportExcel() {
    if (!state.lastTable || !state.bundle) return;
    const current = check(), table = state.lastTable, bundle = state.bundle;
    const rows = [
      [current.id + ' · ' + current.title],
      ['MODEL', bundle.modelName], ['SOURCE', bundle.runId || bundle.sourceLabel],
      ['FORMAL_COMPLIANCE', 'NOT_PROVEN'], ['ENGINEERING_RELEASE', 'NOT_READY'],
      [], table.headers, ...table.rows.map(row => row.map(value => value ?? '')), [],
      ['SCOPE', table.note], ['SOURCE SHA-256', bundle.sourceSha],
      ...(bundle.resultSha ? [['RESULTS SHA-256', bundle.resultSha]] : []),
    ];
    const url = URL.createObjectURL(xlsx(rows));
    const link = node('a');
    link.href = url;
    link.download = 'tbdy-check-' + current.id.replace('.', '-') + '.xlsx';
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    window.engineConsole.log('info', 'EXPORT', 'Saved the displayed table with source traceability.');
  }

  document.addEventListener('click', event => {
    const target = event.target.closest('button');
    if (!target) return;
    if (target.dataset.deskCheck) {
      selectCheck(target.dataset.deskCheck);
    } else if (target.dataset.settingsSection) {
      if (state.view !== 'settings' && checkGroups(check().id).length) state.region = checkGroups(check().id)[0];
      openSettings(target.dataset.settingsSection);
    } else if (target.dataset.deskAction === 'settings') {
      openSettings();
    } else if (target.dataset.deskAction === 'source') {
      openSource(check().legacy);
    } else if (target.dataset.comboRegion) {
      state.region = target.dataset.comboRegion;
      renderSettings();
    }
  });
  for (const name of ['Console', 'Section', 'Combos']) {
    byId('inspectorTab' + name).addEventListener('click', () => inspector(name));
  }
  byId('deskQuickResult').addEventListener('click', () => replay());
  byId('deskStrengthSource').addEventListener('change', event => {
    state.settings.columnStrength.source = event.target.value;
    render();
    persistSettings();
  });
  byId('deskStrengthDefaults').addEventListener('change', event => {
    state.settings.columnStrength.defaults = [...event.target.selectedOptions].map(option => option.value);
    render();
    persistSettings();
  });
  byId('deskResetStrength').addEventListener('click', () => {
    state.settings.columnStrength.source = 'ASSIGNED_DESIGN';
    state.settings.columnStrength.defaults = null;
    render();
    persistSettings();
  });
  byId('deskForceColumn').addEventListener('change', event => {
    state.forceColumn = event.target.value;
    renderNativeForces();
  });
  byId('deskPmmMember').addEventListener('change', event => {
    state.pmmMember = event.target.value;
    state.pmmChoice = state.pmmMember && state.bundle?.modelKey
      ? {modelKey: state.bundle.modelKey, memberId: state.pmmMember} : null;
    renderResult();
  });
  byId('deskForceCombination').addEventListener('change', event => {
    state.forceCombination = event.target.value;
    renderNativeForces();
  });
  byId('deskF04Check').addEventListener('click', () => replay(true));
  byId('deskGeneralCheck').addEventListener('click', () => {
    emit('tbdy:request-model-audit', {checks: [...checks.keys()].filter(id => id.startsWith('1.'))});
    replay(true);
  });
  byId('deskExcel').addEventListener('click', exportExcel);
  byId('deskAddCombo').addEventListener('click', () => editCombos(true));
  byId('deskRemoveCombo').addEventListener('click', () => editCombos(false));
  byId('deskResetRegion').addEventListener('click', () => {
    delete state.settings.assignments[state.scope][state.region];
    render();
    persistSettings();
  });
  byId('deskAvailable').addEventListener('change', refreshComboButtons);
  byId('deskAssigned').addEventListener('change', refreshComboButtons);
  byId('deskComboScope').addEventListener('change', event => {
    state.scope = event.target.value;
    renderSettings();
    renderCombos();
  });
  byId('deskBasement').addEventListener('change', event => {
    state.settings.basement = event.target.checked;
    if (!state.settings.basement) state.scope = 'upper';
    persistSettings();
    renderSettings();
    renderCombos();
  });
  byId('deskBasementLevel').addEventListener('change', event => {
    const value = event.target.valueAsNumber;
    if (Number.isFinite(value)) {
      state.settings.level = value;
      persistSettings();
    } else {
      event.target.value = state.settings.level;
    }
  });

  for (const [id, setter] of [
    ['deskBeamTopContDia', el => { state.settings.beamSelection.top_continuous.diameter_mm = Number(el.value); }],
    ['deskBeamTopContCount', el => { const v = Math.max(2, Math.round(el.valueAsNumber || 2)); el.value = v; state.settings.beamSelection.top_continuous.count = v; }],
    ['deskBeamBotContDia', el => { state.settings.beamSelection.bottom_continuous.diameter_mm = Number(el.value); }],
    ['deskBeamBotContCount', el => { const v = Math.max(2, Math.round(el.valueAsNumber || 2)); el.value = v; state.settings.beamSelection.bottom_continuous.count = v; }],
    ['deskBeamConfDia', el => { state.settings.beamSelection.stirrup_confinement.diameter_mm = Number(el.value); }],
    ['deskBeamConfSpacing', el => { if (el.valueAsNumber > 0) state.settings.beamSelection.stirrup_confinement.spacing_mm = el.valueAsNumber; else el.value = state.settings.beamSelection.stirrup_confinement.spacing_mm; }],
    ['deskBeamConfLegs', el => { state.settings.beamSelection.stirrup_confinement.legs = Number(el.value); }],
    ['deskBeamSpanDia', el => { state.settings.beamSelection.stirrup_span.diameter_mm = Number(el.value); }],
    ['deskBeamSpanSpacing', el => { if (el.valueAsNumber > 0) state.settings.beamSelection.stirrup_span.spacing_mm = el.valueAsNumber; else el.value = state.settings.beamSelection.stirrup_span.spacing_mm; }],
    ['deskBeamSpanLegs', el => { state.settings.beamSelection.stirrup_span.legs = Number(el.value); }],
    ['deskBeamStrictOver', el => { state.settings.beamSelection.strictly_exceed_required = el.checked; }],
    ['deskColConfSpacing', el => { if (el.valueAsNumber > 0) state.settings.columnSelection.stirrup_confinement_spacing_mm = el.valueAsNumber; else el.value = state.settings.columnSelection.stirrup_confinement_spacing_mm; }],
    ['deskColSpanSpacing', el => { if (el.valueAsNumber > 0) state.settings.columnSelection.stirrup_span_spacing_mm = el.valueAsNumber; else el.value = state.settings.columnSelection.stirrup_span_spacing_mm; }],
  ]) {
    const node = byId(id);
    if (!node) continue;
    node.addEventListener('change', event => {
      setter(event.target);
      persistSettings();
      render();
    });
  }
  byId('deskTightenStirrups')?.addEventListener('click', () => {
    state.settings.beamSelection.stirrup_confinement = {diameter_mm: 10, spacing_mm: 90, legs: 4};
    state.settings.beamSelection.stirrup_span = {diameter_mm: 10, spacing_mm: 150, legs: 2};
    state.settings.columnSelection.stirrup_confinement_spacing_mm = 90;
    byId('deskRebarStatus').textContent = 'Applied TBDY stirrup tightening preset (beams Φ10/90 · 4 legs, columns 90 mm). Click "Apply to selected run" to recalculate.';
    persistSettings();
    render();
  });
  byId('deskResetRebar').addEventListener('click', () => {
    state.settings.beamSelection = defaultBeamSelection();
    state.settings.columnSelection = defaultColumnSelection();
    byId('deskRebarStatus').textContent = 'Reset beam and column rebar settings to defaults.';
    persistSettings();
    render();
  });
  function runSelection(wholeBuilding) {
    const working = workingSettings();
    const storeys = byId('deskBuildingHingeStoreys').value.trim();
    emit('tbdy:apply-rebar-selection', {
      runId: state.bundle?.runId ?? null,
      beamSelection: working.beamSelection,
      columnSelection: working.columnSelection,
      wholeBuilding,
      wallHingeStoreys: wholeBuilding && storeys ? storeys.split(',').map(name => name.trim()) : undefined,
    });
  }
  byId('deskApplyRebar').addEventListener('click', () => runSelection(false));
  byId('deskRunBuilding').addEventListener('click', () => runSelection(true));

  window.TBDYWorkspace = Object.freeze({
    setData,
    setLiveBusy(value) {state.liveBusy = value; render();},
    setLoader(loader) {loadResult = typeof loader === 'function' ? loader : undefined;},
    openCheck: selectCheck,
    openSettings,
    getState() {
      return structuredClone({selectedCheck: state.selected, view: state.view,
        settingsSection: state.settingsSection, assignments: workingSettings(), pmmMember: state.pmmMember});
    },
  });
  buildNavigation();
  selectCheck(state.selected);
})();
