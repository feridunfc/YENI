/* VS02: project-owned check tree and combined, bounded ETABS quick-screening UI. */
(() => {
  'use strict';
  let definitions = [];
  let latest = null;
  let latestExtra = null;
  let latestVs04 = null;
  let latestVs04Numerics = null;
  let latestVs04Readiness = null;
  let latestVs04Pipeline = null;
  let latestFullRun = null;
  let latestCompleteReport = null;
  let latestB2 = null;
  let b2LoadNote = 'No combined ETABS run selected.';
  let b2Request = 0;
  let b1Request = 0;
  let c2Request = 0;
  const nav = document.getElementById('nav');
  const byId = id => document.getElementById(id);
  const eventLog = (level, stage, message) =>
    window.engineConsole?.log?.(level, stage, message);
  const exportActions = document.createElement('div');
  exportActions.className = 'actions';
  exportActions.id = 'quickExportActions';
  const exportTitle = document.createElement('span');
  exportTitle.className = 'muted small';
  exportTitle.textContent = 'Read ETABS data to export the full report or JSON.';
  const chooseRun = document.createElement('select');
  chooseRun.className = 'field';
  chooseRun.style.width = 'auto';
  chooseRun.setAttribute('aria-label', 'Run to include in the report');
  const jsonButton = document.createElement('button');
  jsonButton.className = 'go'; jsonButton.type = 'button';
  jsonButton.textContent = 'Export full JSON';
  const printButton = document.createElement('button');
  printButton.className = 'go'; printButton.type = 'button';
  printButton.textContent = 'Engineering report / PDF';
  let selectedRunId = '';
  let activeScenarioQuery = '';
  function setExportRun(runId, caption) {
    if (!/^RUN-[a-f0-9]{32}$/.test(runId || '')) return;
    if (![...chooseRun.options].some(o => o.value === runId)) {
      const option = document.createElement('option');
      option.value = runId;
      option.textContent = caption || runId;
      chooseRun.prepend(option);
    }
    chooseRun.value = runId;
    selectedRunId = runId;
    activeScenarioQuery = '';
    jsonButton.disabled = false;
    printButton.disabled = false;
    exportTitle.textContent = 'All recorded checks, source data, and member rows.';
  }
  jsonButton.disabled = true;
  printButton.disabled = true;
  chooseRun.addEventListener('change', () => {
    selectedRunId = chooseRun.value;
    activeScenarioQuery = '';
    const chosen = cachedHistory.find(r => r.run_id === selectedRunId);
    if (chosen) selectSavedRun(chosen);
  });
  jsonButton.addEventListener('click', () => {
    if (!selectedRunId) return;
    window.location.assign('/api/export-checks?run_id=' + encodeURIComponent(selectedRunId) + activeScenarioQuery);
  });
  printButton.addEventListener('click', () => {
    if (!selectedRunId) return;
    window.open('/report/print?run_id=' + encodeURIComponent(selectedRunId) + activeScenarioQuery, '_blank', 'noopener');
  });
  exportActions.append(exportTitle, chooseRun, jsonButton, printButton);
  const reportStatus = byId('quickStatus');
  reportStatus?.insertAdjacentElement('afterend', exportActions);
  let cachedHistory = [];
  let quickHistoryLoaded = false;
  let initialModalRun = null;
  function make(tag, value, css) {
    const e = document.createElement(tag);
    if (value !== undefined) e.textContent = String(value);
    if (css) e.className = css;
    return e;
  }
  const displayNumbers = new Map([2, 4, 6].map(digits => [digits, new Intl.NumberFormat('en-GB', {
    maximumFractionDigits: digits, useGrouping: false
  })]));
  function displayNumber(raw, digits = 4) {
    if (raw == null) return '—';
    if (!/^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:e[+-]?[0-9]+)?$/i.test(String(raw))) return raw;
    const value = Number(raw);
    if (!Number.isFinite(value)) return raw;
    if (value === 0) return '0';
    if (Math.abs(value) < 10 ** -digits || Math.abs(value) >= 1e15) {
      const [mantissa, power] = value.toExponential(2).split('e');
      return displayNumbers.get(2).format(Number(mantissa)) + 'e' + power;
    }
    return displayNumbers.get(digits).format(value);
  }
  function numberCell(raw, digits) {
    const shown = displayNumber(raw, digits);
    const cell = make('td', shown);
    if (raw != null && String(shown) !== String(raw)) cell.title = String(raw);
    return cell;
  }
  function memberRosterCell(item) {
    const cell = make('td');
    for (const row of item.members_by_story ?? []) {
      cell.append(make('div', `${row.story ?? 'Unknown story'} · ${row.member_ids_text}`));
    }
    return cell;
  }
  function tableOf(check, grouped = true) {
    const scroll = make('div', undefined, 'modal-table-scroll');
    const table = make('table', undefined, 'modal-source-table');
    const head = make('thead');
    const tr = make('tr');
    const rosterColumns = grouped ? ['Members', 'Member IDs by story'] : ['Story', 'Member'];
    for (const x of [...rosterColumns, 'Section', 'Material', 'Material classification',
      't2 (mm)', 't3 (mm)', 'Value', 'Limit', 'Ratio', 'Status', 'Diagnostic']) {
      const th = make('th', x); th.scope = 'col'; tr.append(th);
    }
    head.append(tr); table.append(head);
    const body = make('tbody');
    for (const item of (grouped ? check.member_groups : check.items) || []) {
      const row = make('tr');
      if (grouped) row.append(make('td', item.member_count), memberRosterCell(item));
      else row.append(make('td', item.story ?? '—'), make('td', item.element_id ?? '—'));
      for (const value of [item.section, item.material_name, item.material_classification]) {
        row.append(make('td', value ?? '—'));
      }
      row.append(numberCell(item.width_mm, 2), numberCell(item.depth_mm, 2),
        numberCell(item.value), numberCell(item.limit), numberCell(item.ratio),
        make('td', item.status ?? '—'), make('td', item.reason ?? '—'));
      body.append(row);
    }
    table.append(body); scroll.append(table);
    return scroll;
  }
  function renderQuick(report, tab) {
    const host = byId(tab === 7 ? 'quickReport' : 'geomTabPanel');
    if (!host) return;
    host.replaceChildren();
    if (!report) {host.append(make('p', 'No geometry screening has run for this model.', 'muted small')); return;}
    host.append(make('p', `Source: ${report.source_units || 'units unverified'} · ${report.status} · ${report.scope_note || ''}`, 'muted small'));
    if (report.reason) host.append(make('p', `Schema review required: ${report.reason}`, 'warn'));
    if (report.status === 'SCREENING_PARTIAL') host.append(make('p', 'Some members have unresolved sections, material types, or mappings. The concrete checks exclude members with verified non-concrete materials.', 'warn'));
    const visible = (report.checks || []).filter(c => tab === 7 ||
      definitions.some(d => d.check_id === c.check_id && d.tab_id === tab));
    for (const check of visible) {
      const section = make('section', undefined, 'quick-check');
      section.dataset.checkPanel = check.check_id;
      const heading = make('h3', `${check.title} · ${check.status}`);
      const counts = make('p', `Evaluated: ${check.evaluated_count}/${check.expected_count} · Met: ${check.met_count} · Not met: ${check.unmet_count} · Not applicable: ${check.not_applicable_count || 0} · Non-concrete: ${check.proven_non_concrete_count || 0} · Unresolved: ${check.not_proven_count}`, 'muted small');
      section.append(heading, counts);
      if (check.items?.length) {
        if (check.member_groups?.length) section.append(tableOf(check));
        const details = make('details');
        details.append(make('summary', `Individual member rows (${check.items.length})`), tableOf(check, false));
        section.append(details);
      }
      host.append(section);
    }
    if (report.observed_schemas) {
      const details = make('details'); details.append(make('summary', 'Source table schema and diagnostics'));
      details.append(make('pre', JSON.stringify(report.observed_schemas, null, 2))); host.append(details);
    }
  }
  function renderExtras(tab) {
    byId('vs06-b1-panel')?.classList.toggle('hidden', tab !== 9);
    const host = byId('extraTabPanel');
    if (!host || (tab !== 1 && tab !== 9)) return;
    host.replaceChildren();
    if (!latestExtra) {
      host.append(make('p', 'Run a live scan to obtain VS03 results.', 'muted small'));
      return;
    }
    for (const check of (latestExtra.checks || []).filter(c =>
           definitions.some(def => def.check_id === c.check_id && def.tab_id === tab))) {
      const section = make('section', undefined, 'quick-check');
      section.dataset.checkPanel = check.check_id;
      section.append(make('h3', `${check.title} · ${check.status}`),
                     make('p', `Expected ${check.expected_count} · Calculated ${check.evaluated_count} · Unresolved ${check.not_proven_count}. Formal compliance is NOT_PROVEN.`, 'muted small'));
      const warnings = (check.items || []).filter(item => item.status === 'A1_OBSERVED');
      if (warnings.length) section.append(make('p',
        'A1 TORSIONAL IRREGULARITY OBSERVED · ' + warnings.length +
        ' story-direction records. Verify the eccentricity basis and applicable TBDY checks.', 'warn'));
      if (check.check_id === 'concrete_fck_25') {
        const roster = latestCompleteReport?.material_member_groups ?? latestFullRun?.material_member_groups;
        if (roster?.length) b1Table(section, ['Material', 'Member type', 'Members', 'Material classification', 'Member IDs by story'],
          roster.map(row => [row.material_name, row.member_type, row.member_count, row.material_classification,
            row.members_by_story.map(group => `${group.story ?? 'Unknown story'} · ${group.member_ids_text}`).join('\n')]));
      }
      const details = make('details'); details.open = check.unmet_count > 0 || warnings.length > 0;
      details.append(make('summary', `${(check.items || []).length} source rows`));
      const scroll = make('div', undefined, 'modal-table-scroll');
      const table = make('table', undefined, 'modal-source-table');
      const thead = make('thead'); const tr = make('tr');
      const fields = ['story','direction','source_case','material_name','fck_mpa','eta_bi','value','limit','status','reason'];
      for (const k of fields) {const th=make('th',k); th.scope='col'; tr.append(th);}
      thead.append(tr); table.append(thead);
      const tbody = make('tbody');
      for (const item of (check.items || [])) {
        const row = make('tr');
        for (const key of fields) {
          row.append(['fck_mpa', 'eta_bi', 'value', 'limit'].includes(key)
            ? numberCell(item[key]) : make('td', item[key] ?? '—'));
        }
        tbody.append(row);
      }
      table.append(tbody); scroll.append(table); details.append(scroll); section.append(details); host.append(section);
    }
  }
  function renderVs04() {
    const host = byId('vs04Report');
    if (!host) return;
    host.replaceChildren();
    if (!latestVs04) {
      host.append(make('p', 'Run a live scan to obtain VS04 sources.', 'muted small'));
      return;
    }
    host.append(make('p', 'VS04: ' + latestVs04.status + ' · ' +
      (latestVs04.captured_table_count || 0) + '/3 source tables observed. ' +
      'Engineering field semantics require review.', 'warn'));
    if (latestVs04Numerics) {
      host.append(make('h3', 'VS04 · Source arithmetic — ' + latestVs04Numerics.status));
      host.append(make('p', 'Regulatory checks: 0 · Compliance: NOT_PROVEN · Analysis generation: NOT_PROVEN.', 'muted small'));
      for (const check of latestVs04Numerics.results || []) {
        const details = make('details');
        details.append(make('summary', check.component + ' · ' + check.status + ' · ' +
           check.observed_row_count + '/' + check.expected_row_count));
        details.append(make('pre', JSON.stringify({
          reason_codes: check.reason_codes, items: check.items
        }, null, 2)));
        host.append(details);
      }
    }
    if (latestVs04Readiness) {
      host.append(make('h3', 'VS04-E · Regulatory evidence gates · ' + latestVs04Readiness.status));
      host.append(make('p', 'TBDY regulatory calculations: ' + latestVs04Readiness.regulatory_checks_executed +
        ' / ' + latestVs04Readiness.expected_check_count +
        ' · Compliance NOT_PROVEN.', 'warn'));
      for (const gate of latestVs04Readiness.checks || []) {
        const details = make('details');
        details.append(make('summary', gate.check_id + ' · ' + gate.status));
        details.append(make('pre', JSON.stringify({
          code_ref:gate.code_ref, missing_evidence:gate.missing_evidence,
          source_only_hints:gate.source_only_hints
        }, null, 2)));
        host.append(details);
      }
    }
    if (latestVs04Pipeline) {
      host.append(make('h3', 'VS04 E–J · Source chain for this run · ' + latestVs04Pipeline.status));
      const v2 = latestVs04Pipeline.pipeline_contract_version === 'v2';
      const counts = v2 ? (' · Selection dependency resolved: ' +
        latestVs04Pipeline.source_diagnostic_resolved_count +
        ' · Unresolved sources: ' + latestVs04Pipeline.source_unresolved_count +
        ' · Conditional: ' + latestVs04Pipeline.conditional_component_count) : '';
      host.append(make('p', 'Direct source observation: ' + latestVs04Pipeline.source_observed_count +
        '/' + latestVs04Pipeline.source_component_count + counts +
        ' · Compliance NOT_PROVEN · Engineering release NOT_READY.', 'warn'));
      const diag = latestVs04Pipeline.modal_display_selection_reconciliation;
      if (diag) {
        host.append(make('h3','E/F/G · Response Spectrum Modal Info selection diagnostics'));
        host.append(make('p',diag.status === 'SOURCE_DISPLAY_SELECTION_DEPENDENCY_RECONCILED' ?
           'The initial read failed. Selecting RSX/RSY verified 200 modal rows and resolved the source dependency.' :
           'The initial read could not be reconciled with the selected-case sources.', 'warn'));
        const details = make('details');
        details.append(make('summary', diag.status));
        details.append(make('pre', JSON.stringify(diag, null, 2)));
        host.append(details);
      }
      for (const check of latestVs04Pipeline.checks || []) {
        const details = make('details');
        details.append(make('summary', check.title + ' · ' + check.source_status +
          ' · Evidence status: ' + check.status));
        const source = latestVs04Pipeline.stages?.[check.stage_key] || {};
        details.append(make('pre', JSON.stringify({
          check_id: check.check_id, applicability: check.applicability,
          compliance: check.formal_compliance, reason_codes: check.reason_codes,
          missing_evidence: check.missing_evidence,
          execution_status: check.execution_status, coverage: check.coverage,
          source_identity: check.source_identity,
          source_status: check.source_status, source_facts: source.source_facts,
          conditional_eq_4_19_minimum_term_kn: source.conditional_eq_4_19_minimum_term_kn,
          missing_authorities: source.missing_authorities, mandatory_holds: source.mandatory_holds
        }, null, 2)));
        host.append(details);
      }
    }
    for (const entry of latestVs04.tables || []) {
      const details = make('details');
      details.append(make('summary', entry.table_key + ' · ' + entry.status + ' · ' + (entry.row_count ?? '—') + ' rows'));
      const summary = {fields:entry.fields, field_metadata:entry.field_metadata,
        schema_sha256:entry.schema_sha256, source_sha256:entry.source_sha256,
        reason_codes:entry.reason_codes};
      details.append(make('pre',JSON.stringify(summary,null,2)));
      host.append(details);
    }
  }
  function renderPhysicalExclusions(host, record) {
    if (record?.excluded_stories?.length)
      host.append(make('p', 'NOT_APPLICABLE · ' +
        record.excluded_stories.map(r => r.story).join(', ') +
        ': the complete Frame/Area/Wall/Joint inventory verified that the story is empty.', 'muted small'));
  }
  function renderB2(tab) {
    const panel = byId('b2Panel');
    const host = byId('b2Result');
    if (!panel || !host) return;
    panel.classList.toggle('hidden', tab !== 9);
    host.replaceChildren();
    if (!latestB2) {
      host.append(make('p', b2LoadNote, 'muted small'));
      return;
    }
    const b = latestB2;
    const c = b.comparison_coverage;
    host.append(make('p', b.status + ' · ' + b.numeric_condition, 'warn'));
    host.append(make('p',
      'Story-direction source coverage: ' + b.source_coverage.resolved + '/' + b.source_coverage.expected +
      ' · Adjacent story comparisons: ' + c.resolved + '/' + c.expected +
      ' · Unresolved: ' + c.unresolved +
      ' · Formal B2 classification: NOT_PROVEN', 'muted small'));
    if (b.physical_story_scope) {
      const scope = b.physical_story_scope;
      host.append(make('p', scope.source_inventory_complete ?
        'Physical stories: ' + scope.physical_story_count + '/' + scope.defined_story_count +
        ' defined stories · ' + (b.source_coverage_status || b.status) :
        'The physical story inventory is unverified. Empty-story exclusions require verified evidence. ' +
        scope.reason_codes.join('; '), 'muted small'));
    }
    renderPhysicalExclusions(host, b);
    if (b.story_order) {
      const order = b.story_order;
      host.append(make('p', 'Stories with points at their upper elevation: ' +
        order.point_elevation_confirmed_stories.filter(s => b.stories.some(r => r.story === s)).length + '/' + b.stories.length +
        ' · Intermediate elevation points: ' + (order.intermediate_point_count ?? '—') +
        ' · Lower-boundary points: ' + (order.lower_boundary_point_count ?? '—') +
        '. Intermediate points leave the story elevation and height as defined.', 'muted small'));
    }
    const addTable = (rows, fields) => {
      const scroll = make('div', undefined, 'modal-table-scroll');
      const table = make('table', undefined, 'modal-source-table');
      const head = make('thead'); const hr = make('tr');
      for (const [, label] of fields) {
        const th = make('th', label); th.scope = 'col'; hr.append(th);
      }
      head.append(hr); table.append(head);
      const body = make('tbody');
      for (const item of rows) {
        const tr = make('tr');
        for (const [key] of fields) {
          const value = item[key];
          if (key.includes('normalized_') || key === 'average_drift_m') tr.append(numberCell(value, 6));
          else if (key === 'height_m' || key === 'eta_ki_candidate') tr.append(numberCell(value));
          else tr.append(make('td', Array.isArray(value) ? value.join('; ') : value ?? '—'));
        }
        body.append(tr);
      }
      table.append(body); scroll.append(table); host.append(scroll);
    };
    addTable(b.source_rows, [
      ['story','Story'],['direction','Direction'],['case','Case'],['height_m','h (m)'],
      ['average_drift_m','Avg Drift (m)'],['status','Source'],['reason','Missing or failed']
    ]);
    addTable(b.items, [
      ['story','Current story'],['adjacent_story','Adjacent story'],['neighbour_role','Neighbor'],
      ['direction','Direction'],['case','Case'],['normalized_mean','Avg Driftᵢ / hᵢ'],
      ['adjacent_normalized_mean','Avg Driftⱼ / hⱼ'],['eta_ki_candidate','Candidate ηki'],
      ['status','Numerical status'],['reason_codes','Open issue']
    ]);
    const notes = make('details');
    notes.append(make('summary', 'Calculation scope and assumptions'));
    const list = make('ul');
    for (const note of b.assumptions_notes) list.append(make('li', note));
    notes.append(list); host.append(notes);
    if (b.reason_codes.length) host.append(make('p', b.reason_codes.join('; '), 'warn'));
    host.append(make('p', 'Source: ' + (b.source_payload_sha256 || '—') +
      ' · Calculation: ' + b.result_sha256 + ' · ENGINEERING_RELEASE=NOT_READY', 'muted small'));
  }
  function renderWallGeometry(tab) {
    const panel = byId('wallGeometryPanel'), host = byId('wallGeometryResult');
    if (!panel || !host) return;
    panel.classList.toggle('hidden', tab !== 13);
    host.replaceChildren();
    const r = latestCompleteReport?.wall_geometry;
    if (!r) {
      host.append(make('p', 'No wall geometry calculation for the selected run.', 'muted small'));
      return;
    }
    host.append(make('p', 'Panels evaluated: ' + r.evaluated_count + '/' + r.expected_count +
      ' · Numerical conditions: ' + r.subconditions_evaluated +
      ' · Conditions not met: ' + r.subconditions_unmet +
      ' · Formal compliance NOT_PROVEN', 'warn'));
    const rows = r.items.map(row => {
      const rules = Object.fromEntries(row.subconditions.map(s => [s.rule, s.status]));
      return [row.story, row.element_id, row.section, row.story_height_m, row.panel_height_m,
        row.panel_length_m, row.thickness_mm, row.panel_length_thickness_ratio,
        row.ordinary_branch_minimum_mm, rules.panel_ratio, rules.thickness_250,
        rules.thickness_h16, row.reason];
    });
    b1Table(host, ['Story', 'Area object ID', 'Section', 'Story height (m)', 'h panel (m)', 'l panel (m)',
      'bw (mm)', 'l panel / bw', 'Standart bw,min (mm)', 'Ratio ≥ 6', 'bw ≥ 250', 'bw ≥ h/16', 'Open issue'],
      rows, {3:4, 4:4, 5:4, 6:2, 7:4, 8:2});
    const details = make('details'); details.append(make('summary', 'Scope, exceptions, and source'));
    const notes = make('ul');
    for (const note of r.assumptions_notes) notes.append(make('li', note));
    details.append(notes);
    b1Table(details, ['Clause', 'Status', 'Missing evidence'],
      r.unevaluated_requirements.map(x => [x.code_ref, x.status, x.reason]));
    details.append(make('p', 'Source: ' + (r.source_payload_sha256 || '—') +
      ' · Result: ' + r.result_sha256, 'micro'));
    host.append(details);
    if (r.reason_codes.length) host.append(make('p', r.reason_codes.join('; '), 'warn'));
  }
  function renderSourceControls(tab) {
    renderAnalysisSetup(tab);
    const specs = [
      ['concrete_fck_80', 1, 'concreteUpperPanel', 'concreteUpperResult',
        [['material_name','Material'], ['fck_mpa','Source Fc (MPa)'], ['limit','Upper limit (MPa)'],
         ['strength_scope_observation','Numerical scope'], ['status','Subcondition'], ['reason','Open issue']]],
      ['modal_combination_spacing', 7, 'modalSpacingPanel', 'modalSpacingResult',
        [['direction','Direction'], ['source_case','Case'], ['modal_combination','Modal combination'],
         ['directional_combination','Directional combination'], ['mode_count','Mode count'],
         ['maximum_period_ratio','Maximum short-to-long period ratio'], ['spacing_status','SRSS separation'],
         ['method_condition','Method condition'], ['reason','Open issue']]],
      ['earthquake_100_30', 5, 'earthquakeRatioPanel', 'earthquakeRatioResult',
        [['combination','Combination'], ['operator','Operator'], ['coefficient_x','X coefficient'],
         ['coefficient_y','Y coefficient'], ['common_factor','Common magnitude'], ['minor_major_ratio','Minor / major'],
         ['dominant_direction','Dominant direction'], ['status','Subcondition'], ['reason','Scope and diagnostics']]],
      ['earthquake_direction_pairs', 5, 'earthquakePairPanel', 'earthquakePairResult',
        [['common_factor','Common magnitude'], ['other_case_coefficients','Other case coefficients'],
         ['x_combinations','X dominant'], ['y_combinations','Y dominant'], ['missing_directions','Unobserved direction'],
         ['observed_sign_patterns','Observed signs'], ['unresolved_combination','Unresolved combination'],
         ['status','Source coverage'], ['reason','Open issue']]]
    ];
    for (const [id, targetTab, panelId, resultId, columns] of specs) {
      const panel = byId(panelId), host = byId(resultId);
      if (!panel || !host) continue;
      panel.classList.toggle('hidden', tab !== targetTab);
      host.replaceChildren();
      const check = [...(latestCompleteReport?.source_controls?.checks || []),
        ...(latestCompleteReport?.earthquake_combinations?.checks || [])].find(c => c.check_id === id);
      if (!check) {
        host.append(make('p', 'No source for this subcondition in the selected run.', 'muted small'));
        continue;
      }
      host.append(make('p', check.code_ref + ' · Calculated ' + check.evaluated_count + '/' +
        check.expected_count + ' · Not applicable ' + (check.not_applicable_count || 0) +
        ' · ' + check.status + ' · Formal compliance NOT_PROVEN', 'muted small'));
      const display = value => Array.isArray(value) ? value.join('; ') :
        value && typeof value === 'object' ? Object.entries(value).map(([key, v]) => key + ': ' + v).join('; ') : value;
      const digits = {fck_mpa:2, limit:2, maximum_period_ratio:4,
        coefficient_x:4, coefficient_y:4, common_factor:4, minor_major_ratio:4};
      const numericColumns = Object.fromEntries(columns.flatMap(([key], i) => digits[key] ? [[i, digits[key]]] : []));
      b1Table(host, columns.map(c => c[1]), check.items.map(row => columns.map(c => display(row[c[0]]))), numericColumns);
      const alternatives = check.items.filter(row => row.envelope_alternatives?.length);
      if (alternatives.length) {
        const detail = make('details'); detail.append(make('summary', 'Envelope alternatives'));
        b1Table(detail, ['Envelope', 'Alternative', 'Factor', 'Source type'],
          alternatives.flatMap(row => row.envelope_alternatives.map(term =>
            [row.combination, term.ref, term.factor, term.ref_type])), {2:4});
        host.append(detail);
      }
      for (const item of check.items) {
        if (!item.pairs?.length) continue;
        const detail = make('details');
        detail.append(make('summary', item.source_case + ' · ' + item.tested_adjacent_pair_count +
          ' adjacent pairs / ' + item.all_distinct_pair_count + ' distinct pairs · Adjacent pairs failing separation: ' +
          item.unmet_adjacent_pair_count));
        b1Table(detail, ['Short-period mode', 'Long-period mode', 'Short period (s)', 'Long period (s)', 'Ratio < 0.8', 'Subcondition'],
          item.pairs.map(p => [p.short_mode, p.long_mode, p.short_period_s, p.long_period_s, p.period_ratio, p.status]),
          {2:4, 3:4, 4:4});
        host.append(detail);
      }
      const notes = make('details'); notes.append(make('summary', 'Scope and source'));
      const list = make('ul');
      for (const note of check.assumptions_notes) list.append(make('li', note));
      notes.append(list, make('p', check.unevaluated_requirements.join('; '), 'micro'),
        make('p', 'Source: ' + JSON.stringify(check.source_provenance) + ' · Calculation: ' + check.result_sha256, 'micro'));
      host.append(notes);
      if (check.reason_codes.length) host.append(make('p', check.reason_codes.join('; '), 'warn'));
    }
  }
  function renderAnalysisSetup(tab) {
    const panel = byId('analysisSetupPanel'), host = byId('analysisSetupResult');
    if (!panel || !host) return;
    panel.classList.toggle('hidden', tab !== 5);
    host.replaceChildren();
    const setup = latestCompleteReport?.analysis_setup || latestFullRun?.analysis_setup;
    if (!setup) {
      host.append(make('p', 'No R03 setup in the selected run.', 'muted small'));
      return;
    }
    host.append(make('p', setup.status + ' · Cases: ' + (setup.case_definition_count ?? '—') +
      ' · Combinations: ' + (setup.typed_graph_source_sha256 ? setup.defined_combination_names.length : '—') +
      ' · Design selections: ' + (setup.design_selection_count ?? 'source unread'), 'warn'));
    const blockers = make('ul');
    for (const code of setup.blocker_codes) blockers.append(make('li', code));
    host.append(blockers);
    if (setup.design_selection?.length) b1Table(host, ['ETABS design list', 'Combination'],
      setup.design_selection.map(row => [row.design_type, row.combination]));
    const details = make('details');
    details.append(make('summary', 'Combination definitions and linear static case settings'));
    b1Table(details, ['Defined combination', 'Operator', 'Spectrum case references', 'Observed design lists', 'Vector constraint'],
      setup.combination_audit.map(row => [row.combination, row.operator,
        row.spectral_case_references.join(', '), row.observed_design_types?.join(', '),
        row.nonconcurrent_source_reasons.join(', ')]));
    b1Table(details, ['Linear static case', 'StiffType', 'NonlinCase'],
      setup.linear_static_settings.map(row => [row.case, row.stiffness_setting, row.nonlinear_case]));
    details.append(make('p', 'Source table SHA-256 ' + setup.source_tables_sha256, 'micro'));
    host.append(details);
  }
  async function loadB2(runId) {
    const request = ++b2Request;
    const b1Version = b1Request;
    latestB2 = null;
    b2LoadNote = runId ? 'Loading B2 for the selected run…' : 'No combined ETABS run selected.';
    renderB2(active);
    renderWallGeometry(active);
    renderSourceControls(active);
    if (!runId) return;
    try {
      // Same report/evaluator as JSON and printable HTML. No browser arithmetic,
      // source mutation, or extra ETABS acquisition.
      const response = await fetch('/api/export-checks?run_id=' + encodeURIComponent(runId),
                                   {cache: 'no-store'});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const report = await response.json();
      if (request !== b2Request) return;
      if (report.run_id !== runId) throw new Error('Run ID mismatch.');
      latestCompleteReport = report;
      latestB2 = report.soft_story_b2 || null;
      b2LoadNote = 'This run has no story drift source for B2.';
      if (b1Version === b1Request) {
        if (report.vs06_b1_result) {
          showB1({result: report.vs06_b1_result, run_id: runId});
          byId('b1Status').textContent += ' · Uses the assumptions saved with this run.';
        } else {
          byId('b1Status').textContent = 'B1 source is incomplete for the selected run: ' +
            (report.vs06_b1_source_status || 'SOURCE_ABSENT');
        }
      }
      if (latestFullRun?.run_id === runId) {
        latestFullRun = {...latestFullRun, soft_story_b2: latestB2,
          ...(report.story_drift ? {story_drift: report.story_drift} : {})};
        renderStoryDrift(report.story_drift || latestFullRun.story_drift || null);
        renderSecondOrder(report.r08_second_order || latestFullRun.r08_second_order || null);
        renderUnifiedTrees(latestFullRun);
      }
    } catch (error) {
      if (request !== b2Request) return;
      latestCompleteReport = null;
      latestB2 = null;
      b2LoadNote = 'Could not open B2 for the selected run: ' + error.message;
      eventLog('error', 'ARCHIVED REPORT', error.message);
      if (b1Version === b1Request)
        byId('b1Status').textContent = 'Could not open B1 for the selected run: ' + error.message;
    }
    renderB2(active);
    renderWallGeometry(active);
    renderSourceControls(active);
    updateCheckStates();
  }
  function checkState(checkId) {
    const report = latestCompleteReport;
    const run = latestFullRun;
    let record;
    if (checkId === 'GLOBAL_SECOND_ORDER') {
      const r08 = report?.r08_second_order || run?.r08_second_order;
      if (!r08) return ['No calculation', '', 'No R08 ETABS source record.'];
      const n = r08.evaluated_story_direction_count || 0;
      return [n ? (n === r08.expected_story_direction_count ? 'Numerical' : 'Partial') : 'Missing',
        'review', r08.status + ' · formal compliance NOT_PROVEN'];
    }
    if (checkId === 'STORY_DRIFT') {
      record = report?.story_drift || run?.story_drift;
      if (!record) return ['No calculation', '', 'No story drift source.'];
      const done = record.evaluated_story_case_direction_count || 0;
      const count = record.expected_story_case_direction_count || 0;
      return [done && done === count ? 'Numerical' : done ? 'Partial' : 'Missing',
              done && done === count ? 'observed' : 'review', record.status];
    }
    if (checkId === 'WEAK_STORY_B1') {
      if (report?.vs06_b1_result) return ['Conditional', 'review', report.vs06_b1_result.b1_numerical.numeric_condition];
      return [report ? 'Missing' : 'No calculation', '', report?.vs06_b1_source_status || 'No B1 source result.'];
    }
    if (checkId === 'SOFT_STORY_B2') {
      if (!latestB2) return ['No calculation', '', b2LoadNote];
      const coverage = latestB2.comparison_coverage;
      return [coverage.resolved ? (coverage.unresolved ? 'Partial' : 'Conditional') : 'Missing',
              'review', latestB2.numeric_condition];
    }
    if (checkId === 'WALL_GEOMETRY_CHECK') {
      const wall = report?.wall_geometry;
      if (wall?.status === 'NOT_APPLICABLE') return ['Not applicable', '', 'Verified non-concrete material.'];
      return [wall?.evaluated_count ? (wall.not_proven_count ? 'Partial' : 'Conditional') : 'Missing',
        'review', wall?.numeric_condition || 'No wall geometry source.'];
    }
    if (['concrete_fck_80', 'modal_combination_spacing', 'earthquake_100_30', 'earthquake_direction_pairs'].includes(checkId)) {
      const check = [...(report?.source_controls?.checks || []),
        ...(report?.earthquake_combinations?.checks || [])].find(c => c.check_id === checkId);
      return [check?.evaluated_count ? (check.unmet_count ? 'Limit exceeded' :
        check.not_proven_count ? 'Partial' : 'Conditional') :
        check?.status === 'NOT_APPLICABLE' ? 'Not applicable' : 'Missing', 'review', check?.status || 'No source.'];
    }
    if (checkId === 'modal_mass_95') record = run?.result || run?.modal;
    else record = (report?.checks || [
      ...(run?.geometry?.checks || []), ...(run?.extra_checks?.checks || [])
    ]).find(c => c.check_id === checkId);
    if (!record) return ['No calculation', '', 'This check is missing from the selected run.'];
    if ((record.items || []).some(x => x.status === 'A1_OBSERVED'))
      return ['A1 observed', 'review', record.status];
    if (record.status === 'A1_CLASSIFIED') return ['Numerical', 'observed', record.status];
    if (record.status?.startsWith('DOES_NOT_MEET')) return ['Outside limit', 'review', record.status];
    if (record.status?.startsWith('MEETS_')) return ['Subcondition', 'observed', record.status];
    if (record.status === 'NOT_APPLICABLE') return ['Not applicable', '', record.status];
    if (record.status?.includes('PARTIAL')) return ['Partial', 'review', record.status];
    return ['Unresolved', 'review', record.status || 'NOT_PROVEN'];
  }
  function updateCheckStates() {
    for (const badge of nav?.querySelectorAll('[data-check-state]') || []) {
      const [label, css, detail] = checkState(badge.dataset.checkState);
      badge.textContent = label;
      badge.className = 'check-state ' + css;
      badge.title = detail + ' · Regulatory compliance NOT_PROVEN';
    }
  }
  function buildTree() {
    if (!nav || !Array.isArray(definitions)) return;
    nav.replaceChildren();
    const categories = {0: 'Model ve kaynaklar', 6: 'Building and seismic',
                        10: 'Reinforced concrete members', 15: 'Foundations'};
    tabs.forEach((title, index) => {
      if (categories[index]) nav.append(make('div', categories[index], 'nav-category'));
      const checks = definitions.filter(d => d.tab_id === index);
      const group = make('div', undefined, 'nav-group');
      const button = make('button', undefined, 'navitem' + (index === active ? ' active' : ''));
      button.type = 'button'; button.dataset.navTab = String(index);
      button.append(make('span', String(index+1).padStart(2,'0')), make('span', title));
      const count = make('span', checks.length ? `${checks.length} CHECKS` : 'PLAN', 'signal' + (checks.length ? ' live' : ''));
      button.append(count); button.addEventListener('click', () => selectTab(index)); group.append(button);
      if (checks.length || index === 12) {
        const children = make('div', undefined, 'nav-children');
        for (const def of checks) {
          const child = make('button', undefined, 'nav-child');
          child.type = 'button'; child.dataset.checkId = def.check_id;
          child.title = def.code_ref;
          const badge = make('span', 'No calculation', 'check-state');
          badge.dataset.checkState = def.check_id;
          child.append(make('span', def.title, 'nav-child-label'), badge);
          child.addEventListener('click', () => {
            selectTab(index);
            const check = def.panel_id ? byId(def.panel_id) :
            def.tab_id === 7 ? document.getElementById('result') :
            byId(def.tab_id === 11 || def.tab_id === 12 ? 'geomTabPanel' : 'extraTabPanel')
              ?.querySelector(`[data-check-panel="${def.check_id}"]`);
            check?.scrollIntoView({block:'nearest', behavior:'smooth'});
          });
          children.append(child);
        }
        if (index === 12) {
          const source = make('button', undefined, 'nav-child');
          source.type = 'button'; source.dataset.sourcePanel = 'columnBankPanel';
          source.append(make('span', 'Force bank and static combinations', 'nav-child-label'),
                        make('span', 'SOURCE', 'check-state'));
          source.addEventListener('click', () => {
            selectTab(12); byId('columnBankPanel')?.scrollIntoView({block:'nearest', behavior:'smooth'});
          });
          children.append(source);
        }
        group.append(children);
      }
      nav.append(group);
    });
    updateCheckStates();
  }
  async function loadRegistry() {
    try {
      const response = await fetch('/api/check-registry', {cache:'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data.checks) || data.checks.length !== data.implemented_check_count) throw new Error('Check registry is inconsistent');
      definitions = data.checks;
      buildTree();
      renderQuick(latest, active);
      renderExtras(active);
    } catch (error) {
      byId('quickStatus').textContent = 'Could not load the check tree: ' + error.message;
      eventLog('error', 'CHECK TREE', error.message);
    }
  }
  function renderUnifiedTrees(data) {
    if (!data || typeof setTree !== 'function') return;
    const inventory = latestCompleteReport?.check_inventory;
    const runId = data.run_id || '';
    const model = data.model_name || 'Source model';
    const mode = data.source_mode === 'LIVE_ETABS' ? 'Live ETABS' :
      data.source_mode === 'OFFLINE_ETABS' ? 'Archived ETABS' :
      data.source_mode === 'SYNTHETIC' ? 'Sentetik test' : 'Recorded source';
    setTree('modeltree', [
      model, mode + ' · Cases: ' + (data.case || 'Modal'),
      'Run: ' + (runId ? runId.slice(-8) : '—')
    ]);
    byId('modeltree').title = model + ' · ' + runId;
    setTree('resulttree', [
      inventory ? inventory.count + ' check records' : 'Check coverage is unverified',
      'Run: ' + (runId ? runId.slice(-8) : '—'),
      'Regulatory compliance: NOT_PROVEN'
    ]);
    updateCheckStates();
  }
  function renderStoryDrift(record) {
    const host = byId("storyDriftReport");
    if (!host) return;
    host.replaceChildren();
    if (!record) {
      host.append(make("p", "The selected run has no story drift source.", "muted small"));
      return;
    }
    host.append(make("h3", "STORY_DRIFT · " + record.status));
    host.append(make("p", "Source numerical result: " +
      record.evaluated_story_case_direction_count + "/" +
      record.expected_story_case_direction_count +
      " · TBDY compliance NOT_PROVEN", "warn"));
    renderPhysicalExclusions(host, record);
    if (record.reason_codes?.length)
      host.append(make("p", "Open: " + record.reason_codes.join(", "), "warn"));
    const table = make("table", undefined, "modal-source-table");
    const head = make("thead"); const hr = make("tr");
    for (const s of ["Story", "Case", "Direction", "h (m)", "Drift", "Δ (mm)", "Fark (mm)"])
      hr.append(make("th", s));
    head.append(hr); table.append(head);
    const body = make("tbody");
    for (const r of (record.items || [])) {
      const tr = make("tr");
      for (const v of [r.story, r.case, r.direction]) tr.append(make("td", v ?? "—"));
      tr.append(numberCell(r.height_m), numberCell(r.etabs_story_drift_ratio, 6),
        numberCell(r.etabs_derived_delta_mm, 2), numberCell(r.etabs_reconciliation_residual_mm, 6));
      body.append(tr);
    }
    table.append(body); const scroller = make("div", undefined, "modal-table-scroll");
    scroller.append(table); host.append(scroller);
    if (record.missing_story_case_direction?.length) {
      const missing = record.missing_story_case_direction.map(x =>
        x.story + "/" + x.case + "/" + x.direction).join(", ");
      host.append(make("p", "Missing coverage: " + missing, "warn"));
    }
  }
  function renderSecondOrder(r08) {
    const host = byId('storyDriftReport');
    if (!host || !r08) return;
    const section = make('section', undefined, 'quick-check');
    section.dataset.checkPanel = 'GLOBAL_SECOND_ORDER';
    section.append(make('h3', 'R08 · Global second-order P–Δ · ' + r08.status),
      make('p', 'Source numerical coverage: ' + r08.evaluated_story_direction_count +
        '/' + r08.expected_story_direction_count +
        ' · Building compliance NOT_PROVEN · Analysis order NOT_PROVEN', 'warn'));
    renderPhysicalExclusions(section, r08);
    const t = make('table', undefined, 'modal-source-table');
    const head = make('thead'), hr = make('tr');
    for (const label of ['Story', 'Direction', 'Case', 'h (m)', 'ΣW (kN)', 'Vi (kN)', 'Ort. Δ (m)', 'Candidate θII'])
      hr.append(make('th', label));
    head.append(hr); t.append(head);
    const body = make('tbody');
    for (const row of (r08.results || [])) {
      const tr = make('tr');
      for (const value of [row.story, row.direction, row.case]) tr.append(make('td', value ?? '—'));
      tr.append(numberCell(row.story_height_m), numberCell(row.cumulative_seismic_weight_kn_candidate, 2),
        numberCell(row.reduced_story_shear_kn_candidate, 2), numberCell(row.etabs_avg_drift_m_candidate, 6),
        numberCell(row.theta_ii_candidate, 6));
      body.append(tr);
    }
    t.append(body);
    const scroll = make('div', undefined, 'modal-table-scroll');
    scroll.append(t); section.append(scroll);
    for (const axis of ['X', 'Y']) {
      const result = r08.direction_results?.[axis];
      if (result) section.append(make('p', axis +
        ': θmax = ' + displayNumber(result.theta_max_candidate, 6) +
        ' · θlimit = ' + displayNumber(result.theta_limit_reference, 6) +
        ' · Candidate βII = ' + displayNumber(result.beta_ii_candidate) +
        ' · TASARIMDA UYGULANMADI', 'muted small'));
    }
    if (r08.reason_codes?.length || r08.missing_authorities?.length) {
      const detail = make('details');
      detail.append(make('summary', 'Open engineering evidence gates'),
        make('pre', JSON.stringify({
          reason_codes: r08.reason_codes || [],
          missing_authorities: r08.missing_authorities || []
        }, null, 2)));
      section.append(detail);
    }
    host.append(section);
  }
  function useReport(report, extra, vs04, vs04Numerics, vs04Readiness, vs04Pipeline, fullRun) {
    latestFullRun = fullRun ? {...fullRun} : null;
    latestCompleteReport = null;
    latestB2 = null;
    b1Request++; c2Request++;
    b1Result = null;
    activeScenarioQuery = '';
    byId('b1Result')?.replaceChildren();
    byId('b1Json').disabled = true;
    byId('b1Html').disabled = true;
    byId('b1UseRun').disabled = false;
    byId('b1Calculate').disabled = false;
    byId('b1Status').textContent = 'Loading B1 sources for the selected run…';
    byId('c2Report')?.replaceChildren();
    byId('c2Calculate').disabled = false;
    byId('c2Status').textContent = 'Calculate the scenario for the selected run.';
    latest = report;
    latestExtra = extra || null;
    latestVs04 = vs04 || null;
    latestVs04Numerics = vs04Numerics || null;
    latestVs04Readiness = vs04Readiness || null;
    latestVs04Pipeline = vs04Pipeline || null;
    renderUnifiedTrees(fullRun);
    renderVs04();
    renderStoryDrift(fullRun?.story_drift || null);
    renderSecondOrder(fullRun?.r08_second_order || null);
    renderExtras(active);
    renderQuick(report, 7);
    renderQuick(report, 11);
    if (active === 12) renderQuick(report, 12);
    loadB2(fullRun?.run_id);
  }
  function selectSavedRun(entry) {
    if (!cachedHistory.some(r => r.run_id === entry.run_id)) cachedHistory.unshift(entry);
    setExportRun(entry.run_id, (entry.model_name || 'ETABS') + ' · ' + entry.run_id.slice(-8));
    useReport(entry.geometry, entry.extra_checks, entry.vs04_schema, entry.vs04_numerics,
              entry.vs04_readiness, entry.vs04_pipeline, entry);
    if (typeof showResult === 'function')
      showResult('Saved modal calculation', {result: entry.modal || entry.result});
    window.showModalFullTable?.(entry.run_id);
    byId('step1').textContent = 'Source: ' + (entry.source_mode || 'archive');
    byId('step2').textContent = entry.vs04_schema?.status || 'Saved schema verified';
    byId('step3').textContent = entry.modal?.status || entry.result?.status || 'NOT_PROVEN';
    byId('quickStatus').textContent = 'Selected run: ' + (entry.model_name || 'ETABS') +
      ' · ' + (entry.captured_at_utc || entry.run_id);
  }
  // Modal-history choices and the full-report selector share one run context.
  window.selectSavedEngineeringRun = (entry, selectShared = true) => {
    if (!selectShared) {
      initialModalRun = entry;
      if (!quickHistoryLoaded || selectedRunId) return;
    }
    const complete = cachedHistory.find(r => r.run_id === entry.run_id);
    selectSavedRun(complete || {...entry, modal: entry.result});
  };
  async function loadQuickHistory() {
    try {
      const response = await fetch('/api/quick-history', {cache:'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const previous = cachedHistory.find(r => r.run_id === selectedRunId);
      cachedHistory = Array.isArray(data.runs) ? data.runs : [];
      if (previous && !cachedHistory.some(r => r.run_id === previous.run_id))
        cachedHistory.push(previous);
      quickHistoryLoaded = true;
      chooseRun.replaceChildren();
      for (const entry of cachedHistory) {
        const option = document.createElement('option');
        option.value = entry.run_id;
        option.textContent = `${entry.model_name || 'ETABS'} · ${entry.captured_at_utc.replace('T', ' ').slice(0, 19)} · ${entry.run_id.slice(-6)}`;
        chooseRun.append(option);
      }
      const requested = typeof sourceQuery === 'undefined' ? null : sourceQuery.get('run');
      const first = cachedHistory.find(r => r.run_id === selectedRunId) ||
                    cachedHistory.find(r => r.run_id === requested) || cachedHistory[0] || initialModalRun;
      if (first) {
        selectSavedRun(first);
      }
    } catch (error) {
      quickHistoryLoaded = true;
      if (!selectedRunId && initialModalRun) selectSavedRun(initialModalRun);
      byId('quickStatus').textContent = 'Could not load the check history: ' + error.message;
      eventLog('error', 'RUN HISTORY', error.message);
    }
  }
  async function runSuite() {
    const button = byId('runAllBtn');
    const status = byId('quickStatus');
    const liveStatus = byId('liveModalStatus');
    const modal = byId('liveCase').value.trim();
    if (!modal) {
      const message = 'A modal case name is required.';
      status.textContent = message;
      liveStatus.textContent = message;
      eventLog('error', 'ETABS', message);
      return;
    }
    button.disabled = true;
    eventLog('info', 'ETABS', 'Combined live scan started · Modal case: ' + modal);
    liveStatus.className = 'live-status';
    liveStatus.textContent = 'Reading ETABS data and preparing sources, units, and results…';
    status.textContent = liveStatus.textContent;
    try {
      // One user gesture -> one existing backend transaction -> one run_id.
      const response = await fetch('/api/live-vs04?case=' + encodeURIComponent(modal),
                                   {method: 'POST', cache: 'no-store'});
      const body = await response.json();
      if (!response.ok) throw new Error(body.result?.reason || body.reason || body.error || 'HTTP ' + response.status);
      if (body.engineering_release !== 'NOT_READY' || !body.vs04_schema || !body.vs04_numerics
          || !body.vs04_readiness || !body.geometry || !body.extra_checks || !body.run_id
          || body.vs04_pipeline?.pipeline_contract_version !== 'v2') {
        throw new Error('INCOMPLETE_OR_UNVERIFIED_UNIFIED_RUN_CONTRACT');
      }
      if (typeof showResult === 'function') showResult('Live ETABS · Combined scan', body);
      if (typeof window.showModalFullTable === 'function') window.showModalFullTable(body.run_id);
      cachedHistory = [{...body, modal: body.result},
                       ...cachedHistory.filter(r => r.run_id !== body.run_id)];
      useReport(body.geometry, body.extra_checks, body.vs04_schema,
                body.vs04_numerics, body.vs04_readiness, body.vs04_pipeline, body);
      setExportRun(body.run_id, (body.model_name || 'ETABS') + ' · combined live run');
      byId('step1').textContent = 'ETABS SOURCE · ' + body.source_rows + ' modal rows';
      byId('step2').textContent = 'SCHEMA · ' + body.vs04_schema.status;
      byId('step3').textContent = 'CALCULATION · ' + body.result.status + ' / RELEASE NOT_READY';
      liveStatus.textContent = 'Run: ' + body.run_id
        + ' · Available checks evaluated · Source: ' + body.vs04_schema.status
        + ' · TBDY compliance: NOT_PROVEN';
      status.textContent = liveStatus.textContent;
      liveStatus.className = 'live-status warn';
      eventLog('success', 'ETABS', 'Combined source and calculation run saved · ' + body.run_id);
      if (body.analysis_setup?.blocker_codes?.length)
        eventLog('warn', 'R03 ANALYSIS SETUP', body.analysis_setup.blocker_codes.join(' | '));
      if (body.r08_second_order) {
        const record = body.r08_second_order;
        const level = record.execution_status === 'SOURCE_NUMERICAL_ONLY' ? 'info' : 'warn';
        eventLog(level, 'R08 GLOBAL P–Δ',
          record.status + ' · ' + record.evaluated_story_direction_count +
          '/' + record.expected_story_direction_count + ' story-directions · NOT_PROVEN');
        if (record.reason_codes?.length)
          eventLog('warn', 'R08 BLOCKERS', record.reason_codes.join(' | '));
        if (record.source_capture_error)
          eventLog('error', 'R08 SOURCE', record.source_capture_error);
      }
      await loadRuns();
    } catch (error) {
      const detail = String(error?.message || error);
      const message = 'Could not complete the combined scan: ' + detail;
      status.textContent = message;
      liveStatus.textContent = message;
      liveStatus.className = 'live-status bad';
      eventLog('error', 'COMBINED SCAN', detail);
      if (/VS04G_PRESENT_UNITS|LIVE_ETABS_UNITS_KN_M_C_REQUIRED/.test(detail)) {
        eventLog('warn', 'ETABS UNITS',
          'The ETABS API did not verify kN·m·°C (code 6) on the connected model. Check the model and API units.');
      }
    } finally {
      button.disabled = false;
    }
  }
  // C2: one read-only source-numeric scenario per selected archived run.
  // Does not invoke COM, alter the original receipt or introduce a second live button.
  const C2_FIELDS = {
    r: 'c2R', i: 'c2I', lambda: 'c2Lambda', material: 'c2Material',
    wall_type: 'c2WallType', flexible_proven: 'c2FlexibleProven',
    wall_mode: 'c2WallMode', wall_load_pattern: 'c2WallLoadPattern', coverage_pct: 'c2Coverage',
    wall_height_m: 'c2WallHeight', opening_pct: 'c2Opening', thickness_m: 'c2Thickness',
    manual_wall_length_m: 'c2ManualLength'
  };
  function c2Query() {
    const query = new URLSearchParams();
    for (const [key, id] of Object.entries(C2_FIELDS)) {
      const el = byId(id);
      query.set(key, key === 'flexible_proven' ? (el.checked ? 'true' : 'false') : el.value);
    }
    return '&' + query.toString();
  }
  async function calculateC2() {
    const status = byId('c2Status');
    const host = byId('c2Report');
    const button = byId('c2Calculate');
    if (!selectedRunId) {
      status.textContent = 'Select an ETABS report run first.';
      return;
    }
    const request = ++c2Request;
    const runId = selectedRunId;
    button.disabled = true;
    host.replaceChildren();
    status.textContent = 'Calculating from the ETABS archive…';
    try {
      const query = c2Query();
      const url = '/api/vs06-drift-scenario?run_id=' + encodeURIComponent(runId) + query;
      const response = await fetch(url, {cache:'no-store'});
      const data = await response.json();
      if (request !== c2Request || selectedRunId !== runId) return;
      if (!response.ok) throw new Error(data.error || 'HTTP ' + response.status);
      if (data.formal_compliance !== 'NOT_PROVEN' || data.engineering_release !== 'NOT_READY'
          || !Array.isArray(data.rows) || !data.scenario_sha256) {
        throw new Error('VS06_SCENARIO_CONTRACT_INCOMPLETE');
      }
      activeScenarioQuery = query;
      status.textContent = 'Conditional calculation: ' + data.source_numeric_count + '/' +
        data.expected_story_direction_count + ' story-directions · Within limit: ' +
        data.conditional_within_count + ' · Above limit: ' +
        data.conditional_exceeds_count + '. Regulatory compliance NOT_PROVEN.';
      host.append(make('p', 'TBDY 2018 Eqs. (4.32)–(4.34) · ETABS Story Drifts × h · User scenario for R/I and λ.', 'muted small'));
      renderPhysicalExclusions(host, data);
      if (data.flexible_capacity_warning)
        host.append(make('p', 'The 0.016κ scenario limit for flexible infill requires documented connection capacity.', 'warn'));
      const wall = data.wall_candidate_inventory || {};
      host.append(make('p', 'Load pattern ' + (wall.load_pattern || 'LC_WDL') + ': ' + wall.source_status +
        ' · Candidate wall-supporting beams: ' + wall.candidate_beam_count +
        ' · Estimated infill length (m): ' + (wall.candidate_total_length_m ?? '—') +
        ' · Net infill area (m²): ' + (wall.assumed_net_face_area_m2 ?? '—') +
        '. Verify against the physical wall inventory.', 'muted small'));
      const scroller = make('div', undefined, 'modal-table-scroll');
      const table = make('table', undefined, 'modal-source-table');
      const thead = make('thead');
      const header = make('tr');
      for (const h of ['Story', 'Direction', 'Case', 'Source Δ (mm)', 'Scenario δ (mm)', 'λδ/h', 'Limit', 'Utilization', 'Conditional result']) {
        const th = make('th', h);
        header.append(th);
      }
      thead.append(header); table.append(thead);
      const tbody = make('tbody');
      for (const row of data.rows) {
        const tr = make('tr');
        for (const value of [row.story, row.direction, row.case])
          tr.append(make('td', value ?? '—'));
        tr.append(numberCell(row.source_delta_mm, 2), numberCell(row.effective_delta_mm, 2),
          numberCell(row.lambda_effective_ratio, 6), numberCell(row.limit, 6),
          numberCell(row.utilization_ratio), make('td', row.conditional_numeric_condition ?? '—'));
        tbody.append(tr);
      }
      table.append(tbody); scroller.append(table); host.append(scroller);
      host.append(make('p', 'Scenario SHA-256: ' + data.scenario_sha256 +
        ' · The JSON and engineering report exports use these same options and results.', 'micro'));
    } catch (err) {
      if (request !== c2Request || selectedRunId !== runId) return;
      activeScenarioQuery = '';
      status.textContent = 'VS06-C2 numerical calculation failed: ' + err.message;
      eventLog('error', 'C2 STORY DRIFT', err.message);
      host.replaceChildren();
    } finally {
      if (request === c2Request) button.disabled = false;
    }
  }
  byId('c2Calculate')?.addEventListener('click', calculateC2);

  let b1Result = null;
  function b1Table(host, headers, rows, numericColumns = {}) {
    const scroll=make('div', undefined, 'modal-table-scroll');
    const table=make('table', undefined, 'modal-source-table');
    const thead=make('thead'), tr=make('tr');
    for(const heading of headers)tr.append(make('th',heading));
    thead.append(tr);table.append(thead);
    const tbody=make('tbody');
    for(const values of rows){
      const row=make('tr');
      values.forEach((value, index) => row.append(numericColumns[index]
        ? numberCell(value, numericColumns[index]) : make('td', value ?? '—')));
      tbody.append(row);
    }
    table.append(tbody);scroll.append(table);host.append(scroll);
  }
  function b1CurrentOptions(){
    return {
      wall_type:byId('b1WallType').value,
      unit_weight_kN_m3:byId('b1Gamma').value,
      unit_weight_min_kN_m3:byId('b1GammaMin').value,
      unit_weight_max_kN_m3:byId('b1GammaMax').value,
      opening_fraction:byId('b1Opening').value,
      low_load_ratio_cutoff:byId('b1Cutoff').value,
      shear_modulus_mpa:byId('b1Shear').value,
      R_base:byId('b1R').value
    };
  }
  function showB1(body){
    const status=byId('b1Status'),host=byId('b1Result');
    if (!body.result || body.result.formal_compliance !== 'NOT_PROVEN'
        || body.result.b1_numerical?.formal_compliance !== 'NOT_PROVEN')
      throw new Error('B1_SOURCE_RESULT_CONTRACT_INVALID');
    host.replaceChildren();
      b1Result=body;
      const r=body.result,number=r.b1_numerical;
      status.textContent='B1 X/Y: '+r.source_candidate_wall_beams+' LC_WDL beams, '+
        r.source_wall_load_rows+' source assignments · Minimum ηci='+displayNumber(number.eta_ci_min)+
        ' · '+number.numeric_condition+' · formal compliance NOT_PROVEN.';
      host.append(make('p','TBDY Table 3.6 · §3.6.2.3 · Aw + Ag + 0.15Ak. Ak is estimated from the applied load using masonry thickness and opening assumptions.','muted small'));
      host.append(make('p', 'Physical story coverage: ' + (r.physical_source_coverage || 'UNKNOWN') +
        '. Adjacent story counts refer to the conditional B1 scenario.', 'muted small'));
      renderPhysicalExclusions(host, r);
      const data=[];
      for(const story of r.story_direction_areas){
        for(const d of ['X','Y']){
          const x=story[d];
          data.push([story.story,d,story.column_count,x.wall_count,x.loaded_beam_count,
            x.loaded_beam_length_m,x.column_Aw_m2,x.wall_Ag_m2,
            x.infill_Ak_assumed_m2,x.infill_shear_stiffness_proxy_kN_m]);
        }
      }
      b1Table(host,['Story','Direction','Column','Wall','LC_WDL beams','Loaded length (m)',
        'Aw m²','Ag m²','Assumed Ak (m²)','K_proxy kN/m'],data, {5:4, 6:2, 7:2, 8:2, 9:2});
      host.append(make('h3','B1 adjacent story comparisons and numerical ηci'));
      b1Table(host,['Lower','Upper','Direction','Lower Ae','Upper Ae','ηci','Numerical result'],
        number.paired_results.map(p=>[p.lower_story,p.upper_story,p.direction,p.Ae_lower_m2,
                                     p.Ae_upper_m2,p.eta_ci,p.numeric_condition]), {3:2, 4:2, 5:4});
      const notes=make('details');notes.append(make('summary','Assumptions and 9/19 cm wall classifications'));
      const ul=make('ol');
      for(const item of r.assumptions_notes)ul.append(make('li',item));
      notes.append(ul);
      b1Table(notes,['ETABS beam','Story','Direction','h_net m','q kN/m','t m',
                     'Opening','Ak m²','K_proxy kN/m'],
        r.beam_assumptions.map(x=>[x.beam_id,x.story,x.direction,x.clear_wall_height_m,
          x.line_load_total_kN_m,x.thickness_m,x.assumed_opening_fraction,
          x.assumed_Ak_m2,x.assumed_stiffness_proxy_kN_m]), {3:4, 4:2, 5:4, 6:4, 7:2, 8:2});
      host.append(notes);
      host.append(make('p','B1 result SHA-256: '+r.result_sha256+
        ' · Model generation and masonry material require separate evidence.','micro'));
      byId('b1Json').disabled=false;byId('b1Html').disabled=false;
  }

  async function calculateB1(){
    const status=byId('b1Status'),host=byId('b1Result'),btn=byId('b1Calculate');
    const a=byId('b1GeometryFile').files[0],b=byId('b1WallFile').files[0];
    if(!a||!b){status.textContent='Select both the B1_GEOMETRY and LC_WDL_OBJECT JSON sources.';return;}
    if(a.size+b.size>6*1024*1024){
      status.textContent='Combined B1 sources must be 6 MB or smaller.';return;
    }
    const request = ++b1Request;
    btn.disabled=true;
    byId('b1Json').disabled=true;
    byId('b1Html').disabled=true;
    b1Result=null;host.replaceChildren();
    status.textContent='Binding sources to X/Y members, LC_WDL, and the B1 rule…';
    try{
      const [geometry,wall_loads]=await Promise.all([a.text(),b.text()]);
      if (request !== b1Request) return;
      const payload={geometry:JSON.parse(geometry),wall_loads:JSON.parse(wall_loads),
                     options:b1CurrentOptions()};
      const response=await fetch('/api/vs06-b1-preview',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify(payload),cache:'no-store'
      });
      const body=await response.json();
      if (request !== b1Request) return;
      if(!response.ok)throw new Error(body.error||'B1_HTTP_'+response.status);
      if(!body.result||!body.html||body.result.formal_compliance!=='NOT_PROVEN'
         ||body.result.b1_numerical?.formal_compliance!=='NOT_PROVEN'){
        throw new Error('B1_SOURCE_RESULT_CONTRACT_INVALID');
      }
      showB1(body);
    }catch(err){
      if (request !== b1Request) return;
      b1Result=null;status.textContent='B1 source calculation rejected: '+err.message;
      eventLog('error', 'B1 SOURCE', err.message);
      host.replaceChildren();
    }finally{
      if (request === b1Request) btn.disabled=false;
    }
  }
  function b1Download(filename,content,mime,openWindow){
    const url=URL.createObjectURL(new Blob([content],{type:mime}));
    if(openWindow){
      window.open(url,'_blank','noopener');
    }else{
      const a=document.createElement('a');a.href=url;a.download=filename;
      document.body.append(a);a.click();a.remove();
    }
    setTimeout(()=>URL.revokeObjectURL(url),60000);
  }
  async function showB1FromRun(){
    const btn=byId('b1UseRun'),status=byId('b1Status');
    if(!selectedRunId){
      status.textContent='Select a combined ETABS run first.';return;
    }
    const request = ++b1Request;
    const runId = selectedRunId;
    btn.disabled=true;
    b1Result=null;
    byId('b1Result').replaceChildren();
    byId('b1Json').disabled=true;
    byId('b1Html').disabled=true;
    status.textContent='Recalculating B1 from the sources in the selected run…';
    try{
      const u='/api/export-checks?run_id='+encodeURIComponent(runId);
      const response=await fetch(u,{cache:'no-store'});
      const report=await response.json();
      if (request !== b1Request || selectedRunId !== runId) return;
      if(!response.ok)throw new Error(report.error||'RUN_REPORT_UNAVAILABLE');
      if(report.run_id !== runId)throw new Error('B1_RUN_ID_MISMATCH');
      if(!report.vs06_b1_result){
        throw new Error('B1 sources are incomplete or absent from this archived run: '+
                        (report.vs06_b1_source_status||'SOURCE_ABSENT')+
                        '. Use the file selectors for the two legacy JSON files.');
      }
      showB1({result:report.vs06_b1_result,run_id:runId});
      status.textContent+=' · Archived assumptions: γ=10 kN/m³, 9/19 cm masonry, conditional 50% opening, Gm=500 MPa.';
    }catch(err){
      if (request !== b1Request || selectedRunId !== runId) return;
      status.textContent='Could not open B1 from the selected ETABS run: '+err.message;
      eventLog('error', 'B1 ARCHIVE', err.message);
    }finally{if (request === b1Request) btn.disabled=false;}
  }
  byId('b1UseRun')?.addEventListener('click',showB1FromRun);
  byId('b1Calculate')?.addEventListener('click',calculateB1);
  byId('b1Json')?.addEventListener('click',()=>{
    if(b1Result)b1Download('B1_SOURCE_NUMERIC.json',
      JSON.stringify(b1Result.result,null,2)+'\n','application/json;charset=utf-8',false);
  });
  byId('b1Html')?.addEventListener('click',()=>{
    if (b1Result?.run_id)
      window.open('/report/print?run_id='+encodeURIComponent(b1Result.run_id), '_blank', 'noopener');
    else if(b1Result)b1Download('B1_SOURCE_NUMERIC.html',
      b1Result.html,'text/html;charset=utf-8',true);
  });
  window.renderQuickChecksForTab = tab => {renderQuick(latest, tab);renderExtras(tab);renderB2(tab);renderWallGeometry(tab);renderSourceControls(tab);};
  byId('runAllBtn')?.addEventListener('click', runSuite);
  loadRegistry();
  loadQuickHistory();
})();
