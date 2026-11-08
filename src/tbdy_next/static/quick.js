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
  let b2LoadNote = 'Birleşik ETABS kaydı henüz seçilmedi.';
  let b2Request = 0;
  let b1Request = 0;
  let c2Request = 0;
  const nav = document.getElementById('nav');
  const byId = id => document.getElementById(id);
  const exportActions = document.createElement('div');
  exportActions.className = 'actions';
  exportActions.id = 'quickExportActions';
  const exportTitle = document.createElement('span');
  exportTitle.className = 'muted small';
  exportTitle.textContent = 'Tam rapor / JSON: ETABS verisini okuyup hesaplayın.';
  const chooseRun = document.createElement('select');
  chooseRun.className = 'field';
  chooseRun.style.width = 'auto';
  chooseRun.setAttribute('aria-label', 'Raporlanacak kayıt');
  const jsonButton = document.createElement('button');
  jsonButton.className = 'go'; jsonButton.type = 'button';
  jsonButton.textContent = 'Tam JSON dışa aktar';
  const printButton = document.createElement('button');
  printButton.className = 'go'; printButton.type = 'button';
  printButton.textContent = 'Mühendislik raporu / PDF';
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
    exportTitle.textContent = 'Kayıtlı kontrollerin tamamı: kaynak veriler + tüm eleman satırları.';
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
  function tableOf(check) {
    const scroll = make('div', undefined, 'modal-table-scroll');
    const table = make('table', undefined, 'modal-source-table');
    const head = make('thead');
    const tr = make('tr');
    for (const x of ['Kat', 'Eleman', 'Kesit', 'Malzeme', 'Malzeme sınıfı', 't2 (mm)', 't3 (mm)', 'Değer', 'Sınır', 'Durum']) {
      const th = make('th', x); th.scope = 'col'; tr.append(th);
    }
    head.append(tr); table.append(head);
    const body = make('tbody');
    for (const item of check.items || []) {
      const row = make('tr');
      for (const value of [item.story, item.element_id, item.section, item.material_name,
                          item.material_classification, item.width_mm, item.depth_mm,
                          item.value, item.limit, item.status]) {
        row.append(make('td', value ?? '—'));
      }
      body.append(row);
    }
    table.append(body); scroll.append(table);
    return scroll;
  }
  function renderQuick(report, tab) {
    const host = byId(tab === 7 ? 'quickReport' : 'geomTabPanel');
    if (!host) return;
    host.replaceChildren();
    if (!report) {host.append(make('p', 'Bu model için henüz hızlı geometri taraması yapılmadı.', 'muted small')); return;}
    host.append(make('p', `Kaynak: ${report.source_units || 'birim doğrulanmadı'} · ${report.status} · ${report.scope_note || ''}`, 'muted small'));
    if (report.reason) host.append(make('p', `Şema incelemesi gerekli: ${report.reason}`, 'warn'));
    if (report.status === 'SCREENING_PARTIAL') host.append(make('p', 'Bazı elemanlarda kesit, malzeme türü veya eşleştirme eksik. Kanıtlı beton dışı elemanlar betonarme kontrolüne dahil edilmez.', 'warn'));
    const visible = (report.checks || []).filter(c => tab === 7 ||
      definitions.some(d => d.check_id === c.check_id && d.tab_id === tab));
    for (const check of visible) {
      const section = make('section', undefined, 'quick-check');
      section.dataset.checkPanel = check.check_id;
      const heading = make('h3', `${check.title} · ${check.status}`);
      const counts = make('p', `İncelenen: ${check.evaluated_count}/${check.expected_count} · Koşulu sağlayan: ${check.met_count} · Sağlamayan: ${check.unmet_count} · Kapsam dışı: ${check.not_applicable_count || 0} · Beton dışı: ${check.proven_non_concrete_count || 0} · Çözümlenemeyen: ${check.not_proven_count}`, 'muted small');
      section.append(heading, counts);
      if (check.items?.length) {
        const details = make('details'); details.open = check.unmet_count > 0;
        details.append(make('summary', `${check.items.length} elemanın tamamını göster`), tableOf(check));
        section.append(details);
      }
      host.append(section);
    }
    if (report.observed_schemas) {
      const details = make('details'); details.append(make('summary', 'Kaynak tablo şeması / hata teşhisi'));
      details.append(make('pre', JSON.stringify(report.observed_schemas, null, 2))); host.append(details);
    }
  }
  function renderExtras(tab) {
    byId('vs06-b1-panel')?.classList.toggle('hidden', tab !== 9);
    const host = byId('extraTabPanel');
    if (!host || (tab !== 1 && tab !== 9)) return;
    host.replaceChildren();
    if (!latestExtra) {
      host.append(make('p', 'VS03 kaydı henüz yok; yukarıdaki tek canlı hesap düğmesini kullanın.', 'muted small'));
      return;
    }
    for (const check of (latestExtra.checks || []).filter(c =>
           definitions.some(def => def.check_id === c.check_id && def.tab_id === tab))) {
      const section = make('section', undefined, 'quick-check');
      section.dataset.checkPanel = check.check_id;
      section.append(make('h3', `${check.title} · ${check.status}`),
                     make('p', `İncelenen: ${check.expected_count}; Hesaplanan: ${check.evaluated_count}; Belirsiz: ${check.not_proven_count}. Formal uygunluk: NOT_PROVEN.`, 'muted small'));
      const warnings = (check.items || []).filter(item => item.status === 'A1_OBSERVED');
      if (warnings.length) section.append(make('p',
        'A1 BURULMA DÜZENSİZLİĞİ GÖZLENDİ · ' + warnings.length +
        ' kat-yön kaydı; dışmerkezlik ve TBDY kapsamı onaylanmadan uygunluk PASS değildir.', 'warn'));
      const details = make('details'); details.open = check.unmet_count > 0 || warnings.length > 0;
      details.append(make('summary', `${(check.items || []).length} kaynak satırı`));
      const scroll = make('div', undefined, 'modal-table-scroll');
      const table = make('table', undefined, 'modal-source-table');
      const thead = make('thead'); const tr = make('tr');
      const fields = ['story','direction','source_case','material_name','fck_mpa','eta_bi','value','limit','status','reason'];
      for (const k of fields) {const th=make('th',k); th.scope='col'; tr.append(th);}
      thead.append(tr); table.append(thead);
      const tbody = make('tbody');
      for (const item of (check.items || [])) {const row=make('tr');for(const k of fields)row.append(make('td',item[k]??'—'));tbody.append(row);}
      table.append(tbody); scroll.append(table); details.append(scroll); section.append(details); host.append(section);
    }
  }
  function renderVs04() {
    const host = byId('vs04Report');
    if (!host) return;
    host.replaceChildren();
    if (!latestVs04) {
      host.append(make('p', 'VS04 kaynak kaydı henüz yok. Yukarıdaki tek canlı hesap düğmesini kullanın.', 'muted small'));
      return;
    }
    host.append(make('p', 'VS04: ' + latestVs04.status + ' · ' +
      (latestVs04.captured_table_count || 0) + '/3 tablo yapısal olarak gözlendi. ' +
      'Alanların mühendislik anlamı onaylanmadı; hesap PASS üretilmedi.', 'warn'));
    if (latestVs04Numerics) {
      host.append(make('h3', 'VS04 · Kaynak aritmetiği — ' + latestVs04Numerics.status));
      host.append(make('p', 'Normatif kontrol: 0 · Uygunluk: NOT_PROVEN · Analiz nesli: NOT_PROVEN.', 'muted small'));
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
      host.append(make('h3', 'VS04-E · Normatif kanıt kapıları · ' + latestVs04Readiness.status));
      host.append(make('p', 'TBDY normatif hesap: ' + latestVs04Readiness.regulatory_checks_executed +
        ' / ' + latestVs04Readiness.expected_check_count +
        ' · Uygunluk NOT_PROVEN. Kaynak aritmetiği yönetmelik kabulü değildir.', 'warn'));
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
      host.append(make('h3', 'VS04 E–J · Tek run_id kaynak zinciri · ' + latestVs04Pipeline.status));
      const v2 = latestVs04Pipeline.pipeline_contract_version === 'v2';
      const counts = v2 ? (' · Seçim bağımlılığı açıklanan: ' +
        latestVs04Pipeline.source_diagnostic_resolved_count +
        ' · Açık kaynak: ' + latestVs04Pipeline.source_unresolved_count +
        ' · Koşullu: ' + latestVs04Pipeline.conditional_component_count) : '';
      host.append(make('p', 'Doğrudan kaynak gözlemi: ' + latestVs04Pipeline.source_observed_count +
        '/' + latestVs04Pipeline.source_component_count + counts +
        ' · TBDY uygunluğu NOT_PROVEN · Mühendislik release NOT_READY.', 'warn'));
      const diag = latestVs04Pipeline.modal_display_selection_reconciliation;
      if (diag) {
        host.append(make('h3','E/F/G · Response Spectrum Modal Info seçim teşhisi'));
        host.append(make('p',diag.status === 'SOURCE_DISPLAY_SELECTION_DEPENDENCY_RECONCILED' ?
           'İlk okuma hatası korunmuştur. RSX/RSY seçimiyle 200 modal satır doğrulandı; kaynak bağlamı açıklanmış, normatif PASS verilmemiştir.' :
           'İlk okuma ve seçilmiş vaka kaynakları uzlaştırılamadı. Kaynak kanıtı açık kalır.', 'warn'));
        const details = make('details');
        details.append(make('summary', diag.status));
        details.append(make('pre', JSON.stringify(diag, null, 2)));
        host.append(details);
      }
      for (const check of latestVs04Pipeline.checks || []) {
        const details = make('details');
        details.append(make('summary', check.title + ' · ' + check.source_status +
          ' · Kanıt statüsü: ' + check.status));
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
      details.append(make('summary', entry.table_key + ' · ' + entry.status + ' · ' + (entry.row_count ?? '—') + ' satır'));
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
        ': tam Frame/Area/Wall/Joint envanteriyle boş olduğu doğrulandı; hesap kapsamından çıkarıldı.', 'muted small'));
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
      'Kaynak kat-yön: ' + b.source_coverage.resolved + '/' + b.source_coverage.expected +
      ' · Komşuluk hesabı: ' + c.resolved + '/' + c.expected +
      ' · Çözülemeyen: ' + c.unresolved +
      ' · Resmî B2 sınıflandırması: NOT_PROVEN', 'muted small'));
    if (b.physical_story_scope) {
      const scope = b.physical_story_scope;
      host.append(make('p', scope.source_inventory_complete ?
        'Fiziksel kat: ' + scope.physical_story_count + '/' + scope.defined_story_count +
        ' tanımlı kat · ' + (b.source_coverage_status || b.status) :
        'Fiziksel kat envanteri doğrulanamadı; boş kat istisnası uygulanmadı. ' +
        scope.reason_codes.join('; '), 'muted small'));
    }
    renderPhysicalExclusions(host, b);
    if (b.story_order) {
      const order = b.story_order;
      host.append(make('p', 'Üst düzlem noktasıyla desteklenen kat: ' +
        order.point_elevation_confirmed_stories.filter(s => b.stories.some(r => r.story === s)).length + '/' + b.stories.length +
        ' · Ara kotlu nokta: ' + (order.intermediate_point_count ?? '—') +
        ' · Alt sınır noktası: ' + (order.lower_boundary_point_count ?? '—') +
        '. Ara noktalar kat kotunu veya yüksekliğini değiştirmez.', 'muted small'));
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
          tr.append(make('td', Array.isArray(value) ? value.join('; ') : value ?? '—'));
        }
        body.append(tr);
      }
      table.append(body); scroll.append(table); host.append(scroll);
    };
    addTable(b.source_rows, [
      ['story','Kat'],['direction','Yön'],['case','Vaka'],['height_m','h (m)'],
      ['average_drift_m','Avg Drift (m)'],['status','Kaynak'],['reason','Eksik / hata']
    ]);
    addTable(b.items, [
      ['story','İncelenen kat'],['adjacent_story','Komşu kat'],['neighbour_role','Komşuluk'],
      ['direction','Yön'],['case','Vaka'],['normalized_mean','Avg Driftᵢ / hᵢ'],
      ['adjacent_normalized_mean','Avg Driftⱼ / hⱼ'],['eta_ki_candidate','ηki adayı'],
      ['status','Sayısal durum'],['reason_codes','Açık neden']
    ]);
    const notes = make('details');
    notes.append(make('summary', 'Hesap kapsamı ve varsayımları'));
    const list = make('ul');
    for (const note of b.assumptions_notes) list.append(make('li', note));
    notes.append(list); host.append(notes);
    if (b.reason_codes.length) host.append(make('p', b.reason_codes.join('; '), 'warn'));
    host.append(make('p', 'Kaynak: ' + (b.source_payload_sha256 || '—') +
      ' · Hesap: ' + b.result_sha256 + ' · ENGINEERING_RELEASE=NOT_READY', 'muted small'));
  }
  function renderWallGeometry(tab) {
    const panel = byId('wallGeometryPanel'), host = byId('wallGeometryResult');
    if (!panel || !host) return;
    panel.classList.toggle('hidden', tab !== 13);
    host.replaceChildren();
    const r = latestCompleteReport?.wall_geometry;
    if (!r) {
      host.append(make('p', 'Seçili kayıtta perde geometrisi hesabı henüz yok.', 'muted small'));
      return;
    }
    host.append(make('p', 'Hesaplanan panel: ' + r.evaluated_count + '/' + r.expected_count +
      ' · Sayısal alt koşul: ' + r.subconditions_evaluated +
      ' · Karşılanmayan alt koşul: ' + r.subconditions_unmet +
      ' · Resmî uygunluk NOT_PROVEN', 'warn'));
    const rows = r.items.map(row => {
      const rules = Object.fromEntries(row.subconditions.map(s => [s.rule, s.status]));
      return [row.story, row.element_id, row.section, row.story_height_m, row.panel_height_m,
        row.panel_length_m, row.thickness_mm, row.panel_length_thickness_ratio,
        row.ordinary_branch_minimum_mm, rules.panel_ratio, rules.thickness_250,
        rules.thickness_h16, row.reason];
    });
    b1Table(host, ['Kat', 'Alan ID', 'Kesit', 'h kat (m)', 'h panel (m)', 'l panel (m)',
      'bw (mm)', 'l panel / bw', 'Standart bw,min (mm)', 'Oran ≥ 6', 'bw ≥ 250', 'bw ≥ h/16', 'Açık neden'], rows);
    const details = make('details'); details.append(make('summary', 'Kapsam, istisnalar ve kaynak'));
    const notes = make('ul');
    for (const note of r.assumptions_notes) notes.append(make('li', note));
    details.append(notes);
    b1Table(details, ['Madde', 'Durum', 'Eksik kanıt'],
      r.unevaluated_requirements.map(x => [x.code_ref, x.status, x.reason]));
    details.append(make('p', 'Kaynak: ' + (r.source_payload_sha256 || '—') +
      ' · Sonuç: ' + r.result_sha256, 'micro'));
    host.append(details);
    if (r.reason_codes.length) host.append(make('p', r.reason_codes.join('; '), 'warn'));
  }
  async function loadB2(runId) {
    const request = ++b2Request;
    const b1Version = b1Request;
    latestB2 = null;
    b2LoadNote = runId ? 'Seçili kaydın B2 hesabı okunuyor…' : 'Birleşik ETABS kaydı henüz seçilmedi.';
    renderB2(active);
    renderWallGeometry(active);
    if (!runId) return;
    try {
      // Same report/evaluator as JSON and printable HTML. No browser arithmetic,
      // source mutation, or extra ETABS acquisition.
      const response = await fetch('/api/export-checks?run_id=' + encodeURIComponent(runId),
                                   {cache: 'no-store'});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const report = await response.json();
      if (request !== b2Request) return;
      if (report.run_id !== runId) throw new Error('Çalışma kimliği uyuşmuyor.');
      latestCompleteReport = report;
      latestB2 = report.soft_story_b2 || null;
      b2LoadNote = 'Bu eski kayıtta B2 için gerekli kat öteleme kaynağı toplanmamış.';
      if (b1Version === b1Request) {
        if (report.vs06_b1_result) {
          showB1({result: report.vs06_b1_result, run_id: runId});
          byId('b1Status').textContent += ' · Seçili kaydın arşiv varsayımları kullanıldı.';
        } else {
          byId('b1Status').textContent = 'Seçili kayıtta B1 kaynağı tamamlanmamış: ' +
            (report.vs06_b1_source_status || 'SOURCE_ABSENT');
        }
      }
      if (latestFullRun?.run_id === runId) {
        latestFullRun = {...latestFullRun, soft_story_b2: latestB2,
          ...(report.story_drift ? {story_drift: report.story_drift} : {})};
        renderStoryDrift(report.story_drift || latestFullRun.story_drift || null);
        renderUnifiedTrees(latestFullRun);
      }
    } catch (error) {
      if (request !== b2Request) return;
      latestCompleteReport = null;
      latestB2 = null;
      b2LoadNote = 'Seçili kaydın B2 sonucu açılamadı: ' + error.message;
      if (b1Version === b1Request)
        byId('b1Status').textContent = 'Seçili kaydın B1 sonucu açılamadı: ' + error.message;
    }
    renderB2(active);
    renderWallGeometry(active);
    updateCheckStates();
  }
  function checkState(checkId) {
    const report = latestCompleteReport;
    const run = latestFullRun;
    let record;
    if (checkId === 'STORY_DRIFT') {
      record = report?.story_drift || run?.story_drift;
      if (!record) return ['Hesap yok', '', 'Kat öteleme kaynağı yok.'];
      const done = record.evaluated_story_case_direction_count || 0;
      const count = record.expected_story_case_direction_count || 0;
      return [done && done === count ? 'Sayısal' : done ? 'Kısmi' : 'Eksik',
              done && done === count ? 'observed' : 'review', record.status];
    }
    if (checkId === 'WEAK_STORY_B1') {
      if (report?.vs06_b1_result) return ['Koşullu', 'review', report.vs06_b1_result.b1_numerical.numeric_condition];
      return [report ? 'Eksik' : 'Hesap yok', '', report?.vs06_b1_source_status || 'B1 kaynak sonucu yok.'];
    }
    if (checkId === 'SOFT_STORY_B2') {
      if (!latestB2) return ['Hesap yok', '', b2LoadNote];
      const coverage = latestB2.comparison_coverage;
      return [coverage.resolved ? (coverage.unresolved ? 'Kısmi' : 'Koşullu') : 'Eksik',
              'review', latestB2.numeric_condition];
    }
    if (checkId === 'WALL_GEOMETRY_CHECK') {
      const wall = report?.wall_geometry;
      if (wall?.status === 'NOT_APPLICABLE') return ['Kapsam dışı', '', 'Kanıtlı beton dışı malzeme.'];
      return [wall?.evaluated_count ? (wall.not_proven_count ? 'Kısmi' : 'Koşullu') : 'Eksik',
        'review', wall?.numeric_condition || 'Perde geometri kaynağı yok.'];
    }
    if (checkId === 'modal_mass_95') record = run?.result || run?.modal;
    else record = (report?.checks || [
      ...(run?.geometry?.checks || []), ...(run?.extra_checks?.checks || [])
    ]).find(c => c.check_id === checkId);
    if (!record) return ['Hesap yok', '', 'Seçili kayıtta bu kontrol bulunmuyor.'];
    if ((record.items || []).some(x => x.status === 'A1_OBSERVED'))
      return ['A1 gözlendi', 'review', record.status];
    if (record.status === 'A1_CLASSIFIED') return ['Sayısal', 'observed', record.status];
    if (record.status?.startsWith('DOES_NOT_MEET')) return ['Eşik dışı', 'review', record.status];
    if (record.status?.startsWith('MEETS_')) return ['Alt koşul', 'observed', record.status];
    if (record.status === 'NOT_APPLICABLE') return ['Kapsam dışı', '', record.status];
    if (record.status?.includes('PARTIAL')) return ['Kısmi', 'review', record.status];
    return ['Belirsiz', 'review', record.status || 'NOT_PROVEN'];
  }
  function updateCheckStates() {
    for (const badge of nav?.querySelectorAll('[data-check-state]') || []) {
      const [label, css, detail] = checkState(badge.dataset.checkState);
      badge.textContent = label;
      badge.className = 'check-state ' + css;
      badge.title = detail + ' · Yönetmelik uygunluğu NOT_PROVEN';
    }
  }
  function buildTree() {
    if (!nav || !Array.isArray(definitions)) return;
    nav.replaceChildren();
    const categories = {0: 'Model ve kaynaklar', 6: 'Bina ve deprem',
                        10: 'Betonarme elemanlar', 15: 'Temeller'};
    tabs.forEach((title, index) => {
      if (categories[index]) nav.append(make('div', categories[index], 'nav-category'));
      const checks = definitions.filter(d => d.tab_id === index);
      const group = make('div', undefined, 'nav-group');
      const button = make('button', undefined, 'navitem' + (index === active ? ' active' : ''));
      button.type = 'button'; button.dataset.navTab = String(index);
      button.append(make('span', String(index+1).padStart(2,'0')), make('span', title));
      const count = make('span', checks.length ? `${checks.length} KONTROL` : 'PLAN', 'signal' + (checks.length ? ' live' : ''));
      button.append(count); button.addEventListener('click', () => selectTab(index)); group.append(button);
      if (checks.length) {
        const children = make('div', undefined, 'nav-children');
        for (const def of checks) {
          const child = make('button', undefined, 'nav-child');
          child.type = 'button'; child.dataset.checkId = def.check_id;
          child.title = def.code_ref;
          const badge = make('span', 'Hesap yok', 'check-state');
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
      if (!Array.isArray(data.checks) || data.checks.length !== data.implemented_check_count) throw new Error('Katalog tutarsız');
      definitions = data.checks;
      buildTree();
      renderQuick(latest, active);
      renderExtras(active);
    } catch (error) {
      byId('quickStatus').textContent = 'Kontrol ağacı yüklenemedi: ' + error.message;
    }
  }
  function renderUnifiedTrees(data) {
    if (!data || typeof setTree !== 'function') return;
    const inventory = latestCompleteReport?.check_inventory;
    const runId = data.run_id || '';
    const model = data.model_name || 'Kaynak model';
    const mode = data.source_mode === 'LIVE_ETABS' ? 'Canlı ETABS' :
      data.source_mode === 'OFFLINE_ETABS' ? 'Arşiv ETABS' :
      data.source_mode === 'SYNTHETIC' ? 'Sentetik test' : 'Kayıtlı kaynak';
    setTree('modeltree', [
      model, mode + ' · Vaka: ' + (data.case || 'Modal'),
      'Çalışma: ' + (runId ? runId.slice(-8) : '—')
    ]);
    byId('modeltree').title = model + ' · ' + runId;
    setTree('resulttree', [
      inventory ? inventory.count + ' kontrol kaydı' : 'Kontrol kapsamı henüz doğrulanmadı',
      'Çalışma: ' + (runId ? runId.slice(-8) : '—'),
      'Yönetmelik uygunluğu: NOT_PROVEN'
    ]);
    updateCheckStates();
  }
  function renderStoryDrift(record) {
    const host = byId("storyDriftReport");
    if (!host) return;
    host.replaceChildren();
    if (!record) {
      host.append(make("p", "Seçili kayıtta kat öteleme kaynağı bulunmuyor.", "muted small"));
      return;
    }
    host.append(make("h3", "STORY_DRIFT · " + record.status));
    host.append(make("p", "Kaynak sayısal sonuç: " +
      record.evaluated_story_case_direction_count + "/" +
      record.expected_story_case_direction_count +
      " · TBDY uygunluğu NOT_PROVEN", "warn"));
    renderPhysicalExclusions(host, record);
    if (record.reason_codes?.length)
      host.append(make("p", "Açık: " + record.reason_codes.join(", "), "warn"));
    const table = make("table", undefined, "modal-source-table");
    const head = make("thead"); const hr = make("tr");
    for (const s of ["Kat", "Vaka", "Yön", "h (m)", "Drift", "Δ (mm)", "Fark (mm)"])
      hr.append(make("th", s));
    head.append(hr); table.append(head);
    const body = make("tbody");
    for (const r of (record.items || [])) {
      const tr = make("tr");
      for (const v of [r.story, r.case, r.direction, r.height_m,
                       r.etabs_story_drift_ratio, r.etabs_derived_delta_mm,
                       r.etabs_reconciliation_residual_mm])
        tr.append(make("td", v ?? "—"));
      body.append(tr);
    }
    table.append(body); const scroller = make("div", undefined, "modal-table-scroll");
    scroller.append(table); host.append(scroller);
    if (record.missing_story_case_direction?.length) {
      const missing = record.missing_story_case_direction.map(x =>
        x.story + "/" + x.case + "/" + x.direction).join(", ");
      host.append(make("p", "Eksik kapsam: " + missing, "warn"));
    }
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
    byId('b1Status').textContent = 'Seçili kaydın B1 kaynakları okunuyor…';
    byId('c2Report')?.replaceChildren();
    byId('c2Calculate').disabled = false;
    byId('c2Status').textContent = 'Seçili kayıt için senaryoyu hesaplayın.';
    latest = report;
    latestExtra = extra || null;
    latestVs04 = vs04 || null;
    latestVs04Numerics = vs04Numerics || null;
    latestVs04Readiness = vs04Readiness || null;
    latestVs04Pipeline = vs04Pipeline || null;
    renderUnifiedTrees(fullRun);
    renderVs04();
    renderStoryDrift(fullRun?.story_drift || null);
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
      showResult('Kaydedilmiş modal hesap', {result: entry.modal || entry.result});
    window.showModalFullTable?.(entry.run_id);
    byId('step1').textContent = 'Kaynak: ' + (entry.source_mode || 'arşiv');
    byId('step2').textContent = entry.vs04_schema?.status || 'Kayıt şeması doğrulandı';
    byId('step3').textContent = entry.modal?.status || entry.result?.status || 'NOT_PROVEN';
    byId('quickStatus').textContent = 'Seçili çalışma: ' + (entry.model_name || 'ETABS') +
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
      const first = cachedHistory.find(r => r.run_id === selectedRunId) ||
                    cachedHistory[0] || initialModalRun;
      if (first) {
        selectSavedRun(first);
      }
    } catch (error) {
      quickHistoryLoaded = true;
      if (!selectedRunId && initialModalRun) selectSavedRun(initialModalRun);
      byId('quickStatus').textContent = 'Geçmiş kontrol kaydı okunamadı: ' + error.message;
    }
  }
  async function runSuite() {
    const button = byId('runAllBtn');
    const status = byId('quickStatus');
    const liveStatus = byId('liveModalStatus');
    const modal = byId('liveCase').value.trim();
    if (!modal) {
      const message = 'Modal vaka adı zorunludur.';
      status.textContent = message;
      liveStatus.textContent = message;
      return;
    }
    button.disabled = true;
    liveStatus.className = 'live-status';
    liveStatus.textContent = 'ETABS verisi okunuyor; kaynaklar, birimler ve kontrol sonuçları hazırlanıyor…';
    status.textContent = liveStatus.textContent;
    try {
      // One user gesture -> one existing backend transaction -> one run_id.
      const response = await fetch('/api/live-vs04?case=' + encodeURIComponent(modal),
                                   {method: 'POST', cache: 'no-store'});
      const body = await response.json();
      if (!response.ok) throw new Error(body.result?.reason || body.reason || 'HTTP ' + response.status);
      if (body.engineering_release !== 'NOT_READY' || !body.vs04_schema || !body.vs04_numerics
          || !body.vs04_readiness || !body.geometry || !body.extra_checks || !body.run_id
          || body.vs04_pipeline?.pipeline_contract_version !== 'v2') {
        throw new Error('INCOMPLETE_OR_UNVERIFIED_UNIFIED_RUN_CONTRACT');
      }
      if (typeof showResult === 'function') showResult('Canlı ETABS · Birleşik tarama', body);
      if (typeof window.showModalFullTable === 'function') window.showModalFullTable(body.run_id);
      cachedHistory = [{...body, modal: body.result},
                       ...cachedHistory.filter(r => r.run_id !== body.run_id)];
      useReport(body.geometry, body.extra_checks, body.vs04_schema,
                body.vs04_numerics, body.vs04_readiness, body.vs04_pipeline, body);
      setExportRun(body.run_id, (body.model_name || 'ETABS') + ' · birleşik canlı çalışma');
      byId('step1').textContent = 'ETABS KAYNAĞI · ' + body.source_rows + ' modal satır';
      byId('step2').textContent = 'ŞEMA · ' + body.vs04_schema.status;
      byId('step3').textContent = 'HESAP · ' + body.result.status + ' / RELEASE NOT_READY';
      liveStatus.textContent = 'Kayıt: ' + body.run_id
        + ' · Mevcut kontroller değerlendirildi · Kaynak: ' + body.vs04_schema.status
        + ' · TBDY genel uygunluk: NOT_PROVEN';
      status.textContent = liveStatus.textContent;
      liveStatus.className = 'live-status warn';
      await loadRuns();
    } catch (error) {
      const message = 'Birleşik tarama tamamlanamadı: ' + error.message;
      status.textContent = message;
      liveStatus.textContent = message;
      liveStatus.className = 'live-status bad';
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
      status.textContent = 'Önce mevcut ETABS rapor kaydını seçin.';
      return;
    }
    const request = ++c2Request;
    const runId = selectedRunId;
    button.disabled = true;
    host.replaceChildren();
    status.textContent = 'ETABS arşivinden sayısal hesap yürütülüyor (yeni COM bağlantısı yok)…';
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
      status.textContent = 'Koşullu hesap: ' + data.source_numeric_count + '/' +
        data.expected_story_direction_count + ' kat/yön; sınır içinde: ' +
        data.conditional_within_count + '; sınırı aşan: ' +
        data.conditional_exceeds_count + '. Yönetmelik uygunluğu NOT_PROVEN.';
      host.append(make('p', 'TBDY 2018 Denk.(4.32)-(4.34) · kaynak: ETABS Story Drifts × h · R/I ve λ kullanıcı senaryosu.', 'muted small'));
      renderPhysicalExclusions(host, data);
      if (data.flexible_capacity_warning)
        host.append(make('p', 'Esnek dolgu için gerekli bağlantı kapasitesi belgesi sağlanmadı; 0.016κ sınırı yalnız senaryodur.', 'warn'));
      const wall = data.wall_candidate_inventory || {};
      host.append(make('p', 'Yük deseni ' + (wall.load_pattern || 'LC_WDL') + ': ' + wall.source_status +
        ' · Duvar adayı kiriş: ' + wall.candidate_beam_count +
        ' · Tahmini dolgu uzunluğu (m): ' + (wall.candidate_total_length_m ?? '—') +
        ' · Net dolgu yüzeyi (m²): ' + (wall.assumed_net_face_area_m2 ?? '—') +
        '. Fiziksel duvar envanteri yerine geçmez.', 'muted small'));
      const scroller = make('div', undefined, 'modal-table-scroll');
      const table = make('table', undefined, 'modal-source-table');
      const thead = make('thead');
      const header = make('tr');
      for (const h of ['Kat', 'Yön', 'Vaka', 'Δ kaynak (mm)', 'δ senaryo (mm)', 'λδ/h', 'Sınır', 'Kullanım', 'Koşullu sonuç']) {
        const th = make('th', h);
        header.append(th);
      }
      thead.append(header); table.append(thead);
      const tbody = make('tbody');
      for (const row of data.rows) {
        const tr = make('tr');
        for (const value of [row.story, row.direction, row.case,
                             row.source_delta_mm, row.effective_delta_mm,
                             row.lambda_effective_ratio, row.limit,
                             row.utilization_ratio, row.conditional_numeric_condition])
          tr.append(make('td', value ?? '—'));
        tbody.append(tr);
      }
      table.append(tbody); scroller.append(table); host.append(scroller);
      host.append(make('p', 'Senaryo SHA-256: ' + data.scenario_sha256 +
        ' · Aynı seçenekler ile Tam JSON / Mühendislik raporu düğmeleri aynı hesap tablosunu dışa aktarır.', 'micro'));
    } catch (err) {
      if (request !== c2Request || selectedRunId !== runId) return;
      activeScenarioQuery = '';
      status.textContent = 'VS06-C2 sayısal hesap başarısız: ' + err.message;
      host.replaceChildren();
    } finally {
      if (request === c2Request) button.disabled = false;
    }
  }
  byId('c2Calculate')?.addEventListener('click', calculateC2);

  let b1Result = null;
  function b1Table(host, headers, rows) {
    const scroll=make('div', undefined, 'modal-table-scroll');
    const table=make('table', undefined, 'modal-source-table');
    const thead=make('thead'), tr=make('tr');
    for(const heading of headers)tr.append(make('th',heading));
    thead.append(tr);table.append(thead);
    const tbody=make('tbody');
    for(const values of rows){
      const row=make('tr');
      for(const value of values)row.append(make('td',value===null||value===undefined?'—':String(value)));
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
      status.textContent='B1 X/Y: '+r.source_candidate_wall_beams+' LC_WDL kiriş, '+
        r.source_wall_load_rows+' gerçek atama; ηci,min='+number.eta_ci_min+
        ' · '+number.numeric_condition+' · resmî uygunluk NOT_PROVEN.';
      host.append(make('p','TBDY Tablo 3.6 · 3.6.2.3 · Aw + Ag + 0.15Ak. Ak yükten tuğla kalınlığı ve boşluk senaryosuyla tahmin edilmiştir.','muted small'));
      host.append(make('p', 'Fiziksel kat kapsamı: ' + (r.physical_source_coverage || 'UNKNOWN') +
        '. Sayısal komşuluk sayısı koşullu B1 aday hesabına aittir.', 'muted small'));
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
      b1Table(host,['Kat','Yön','Kolon','Perde','LC_WDL kiriş','L yüklü m',
        'Aw m²','Ag m²','Ak varsayım m²','K_proxy kN/m'],data);
      host.append(make('h3','B1 kat komşuluğu ve sayısal ηci'));
      b1Table(host,['Alt','Üst','Yön','Ae alt','Ae üst','ηci','Sayısal karar'],
        number.paired_results.map(p=>[p.lower_story,p.upper_story,p.direction,p.Ae_lower_m2,
                                     p.Ae_upper_m2,p.eta_ci,p.numeric_condition]));
      const notes=make('details');notes.append(make('summary','Varsayımlar ve tüm 9/19 cm duvar sınıflandırmaları'));
      const ul=make('ol');
      for(const item of r.assumptions_notes)ul.append(make('li',item));
      notes.append(ul);
      b1Table(notes,['ETABS kiriş','Kat','Yön','h_net m','q kN/m','t m',
                     'Açıklık','Ak m²','K_proxy kN/m'],
        r.beam_assumptions.map(x=>[x.beam_id,x.story,x.direction,x.clear_wall_height_m,
          x.line_load_total_kN_m,x.thickness_m,x.assumed_opening_fraction,
          x.assumed_Ak_m2,x.assumed_stiffness_proxy_kN_m]));
      host.append(notes);
      host.append(make('p','B1 sonuç SHA-256: '+r.result_sha256+
        ' · Model nesli ve tuğla malzemesi ayrıca yetkilendirilmedi.','micro'));
      byId('b1Json').disabled=false;byId('b1Html').disabled=false;
  }

  async function calculateB1(){
    const status=byId('b1Status'),host=byId('b1Result'),btn=byId('b1Calculate');
    const a=byId('b1GeometryFile').files[0],b=byId('b1WallFile').files[0];
    if(!a||!b){status.textContent='B1_GEOMETRY ve LC_WDL_OBJECT JSON kaynaklarının ikisini de seçin.';return;}
    if(a.size+b.size>6*1024*1024){
      status.textContent='B1 kaynakları toplamı 6 MB sınırını geçiyor; güvenli yükleme yapılamadı.';return;
    }
    const request = ++b1Request;
    btn.disabled=true;
    byId('b1Json').disabled=true;
    byId('b1Html').disabled=true;
    b1Result=null;host.replaceChildren();
    status.textContent='Gerçek kaynaklar X/Y eleman, LC_WDL ve B1 kuralına eşleniyor…';
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
      b1Result=null;status.textContent='B1 sayısal kaynak hesabı reddedildi: '+err.message;
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
      status.textContent='Önce ETABS tek tuş çalışma kaydını seçin.';return;
    }
    const request = ++b1Request;
    const runId = selectedRunId;
    btn.disabled=true;
    b1Result=null;
    byId('b1Result').replaceChildren();
    byId('b1Json').disabled=true;
    byId('b1Html').disabled=true;
    status.textContent='Seçili run_id içindeki B1 kaynakları rapordan yeniden hesaplanıyor…';
    try{
      const u='/api/export-checks?run_id='+encodeURIComponent(runId);
      const response=await fetch(u,{cache:'no-store'});
      const report=await response.json();
      if (request !== b1Request || selectedRunId !== runId) return;
      if(!response.ok)throw new Error(report.error||'RUN_REPORT_UNAVAILABLE');
      if(report.run_id !== runId)throw new Error('B1_RUN_ID_MISMATCH');
      if(!report.vs06_b1_result){
        throw new Error('B1 kaynakları bu eski run_id içinde yok veya eksik: '+
                        (report.vs06_b1_source_status||'SOURCE_ABSENT')+
                        '. Eski iki JSON için dosya seçicilerini kullanın.');
      }
      showB1({result:report.vs06_b1_result,run_id:runId});
      status.textContent+=' · Tek tuş kaydında kullanılan B1 varsayılanları: γ=10 kN/m³, 9/19 cm, açıklık %50 koşullu, Gm=500 MPa.';
    }catch(err){
      if (request !== b1Request || selectedRunId !== runId) return;
      status.textContent='Seçili ETABS çalışmasından B1 açılamadı: '+err.message;
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
  window.renderQuickChecksForTab = tab => {renderQuick(latest, tab);renderExtras(tab);renderB2(tab);renderWallGeometry(tab);};
  byId('runAllBtn')?.addEventListener('click', runSuite);
  loadRegistry();
  loadQuickHistory();
})();
