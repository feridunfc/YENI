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
    byId('c2Report')?.replaceChildren();
    const chosen = cachedHistory.find(r => r.run_id === selectedRunId);
    if (chosen) {
      useReport(chosen.geometry, chosen.extra_checks, chosen.vs04_schema, chosen.vs04_numerics, chosen.vs04_readiness, chosen.vs04_pipeline, chosen);
      if (typeof showResult === 'function') {
        showResult('Kaydedilmiş modal hesap', {run_id: chosen.run_id, result: chosen.modal});
      }
      if (typeof window.showModalFullTable === 'function') {
        window.showModalFullTable(chosen.run_id);
      }
    }
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
  function buildTree() {
    if (!nav || !Array.isArray(definitions)) return;
    nav.replaceChildren();
    tabs.forEach((title, index) => {
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
          const child = make('button', def.title, 'nav-child');
          child.type = 'button'; child.dataset.checkId = def.check_id;
          child.title = def.code_ref;
          child.addEventListener('click', () => {
            selectTab(index);
            const check = def.tab_id === 7 ? document.getElementById('result') :
            document.querySelector(`[data-check-panel="${def.check_id}"]`);
            check?.scrollIntoView({block:'nearest', behavior:'smooth'});
          });
          children.append(child);
        }
        group.append(children);
      }
      nav.append(group);
    });
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
    const result = data.result || data.modal || {};
    const extra = data.extra_checks || {};
    const v = data.vs04_schema || {};
    const source = data.vs04_numerics || {};
    const ledger = data.vs04_readiness || {};
    const pipeline = data.vs04_pipeline || null;
    const a1Observed = (extra.checks || [])
      .filter(c => c.check_id === 'a1_torsion_x' || c.check_id === 'a1_torsion_y')
      .flatMap(c => c.items || []).filter(item => item.status === 'A1_OBSERVED');
    setTree('modeltree', [
      'ETABS: ' + (data.model_name || 'kaynak model'),
      'Modal vaka: ' + (data.case || 'Modal'),
      '3 analiz tablosu: ' + (v.captured_table_count ?? '—') + '/3',
      'Tek run_id: ' + (data.run_id || '—')
    ]);
    setTree('resulttree', [
      'Modal kütle: ' + (result.status || 'NOT_PROVEN'),
      ...(a1Observed.length ? ['A1 BURULMA GÖZLENDİ: ' + a1Observed.length +
        ' kat-yön · yönetmelik uygunluğu NOT_PROVEN'] : []),
      ...((data.geometry || {}).checks || []).map(c => c.check_id + ': ' + c.status),
      ...(extra.checks || []).map(c => c.check_id + ': ' + c.status),
      'VS04 kaynak aritmetiği: ' + (source.observed_component_count ?? '—') + '/5',
      ...(pipeline ? (pipeline.checks || []).map(c =>
        c.check_id + ': ' + c.status +
        ((c.reason_codes || []).length ? ' · ' + c.reason_codes.join(', ') : '') +
        ' · FORMAL NOT_PROVEN') :
        ['VS04 E–J kaynak zinciri: henüz toplanmadı']),
      'Normatif kanıt kapıları: ' + (ledger.proven_check_count ?? '—')
        + '/' + (ledger.expected_check_count ?? '—'),
      ...(data.story_drift ? ['STORY_DRIFT: ' + data.story_drift.status +
        ' · Δ hesabı: ' + data.story_drift.evaluated_story_case_direction_count +
        '/' + data.story_drift.expected_story_case_direction_count] : []),
      'Yönetmelik uygunluğu: NOT_PROVEN',
      'ENGINEERING RELEASE: NOT_READY'
    ]);
  }
  function renderStoryDrift(record) {
    const host = byId("vs04Report");
    if (!host || !record) return;
    host.append(make("h3", "STORY_DRIFT · " + record.status));
    host.append(make("p", "Kaynak sayısal sonuç: " +
      record.evaluated_story_case_direction_count + "/" +
      record.expected_story_case_direction_count +
      " · TBDY uygunluğu NOT_PROVEN", "warn"));
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
  }
  async function loadQuickHistory() {
    try {
      const response = await fetch('/api/quick-history', {cache:'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      cachedHistory = Array.isArray(data.runs) ? data.runs : [];
      chooseRun.replaceChildren();
      for (const entry of cachedHistory) {
        const option = document.createElement('option');
        option.value = entry.run_id;
        option.textContent = `${entry.model_name || 'ETABS'} · ${entry.captured_at_utc.replace('T', ' ').slice(0, 19)} · ${entry.run_id.slice(-6)}`;
        chooseRun.append(option);
      }
      const first = cachedHistory[0] || null;
      if (first) {
        useReport(first.geometry, first.extra_checks, first.vs04_schema, first.vs04_numerics, first.vs04_readiness, first.vs04_pipeline, first);
        setExportRun(first.run_id);
        byId('quickStatus').textContent = `Son canlı tarama: ${first.model_name || 'ETABS'} · ${first.captured_at_utc}`;
      }
    } catch (error) {
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
    liveStatus.textContent = 'ETABS okunuyor; şema, birim, 8 mevcut kontrol ve VS04 kaynak kanıtları işleniyor…';
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
      useReport(body.geometry, body.extra_checks, body.vs04_schema,
                body.vs04_numerics, body.vs04_readiness, body.vs04_pipeline, body);
      setExportRun(body.run_id, (body.model_name || 'ETABS') + ' · birleşik canlı çalışma');
      byId('step1').textContent = 'ETABS KAYNAĞI · ' + body.source_rows + ' modal satır';
      byId('step2').textContent = 'ŞEMA · ' + body.vs04_schema.status;
      byId('step3').textContent = 'HESAP · ' + body.result.status + ' / RELEASE NOT_READY';
      liveStatus.textContent = 'Kayıt: ' + body.run_id
        + ' · 8 mevcut kontrol değerlendirildi · VS04: ' + body.vs04_schema.status
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
    button.disabled = true;
    host.replaceChildren();
    status.textContent = 'ETABS arşivinden sayısal hesap yürütülüyor (yeni COM bağlantısı yok)…';
    try {
      const query = c2Query();
      const url = '/api/vs06-drift-scenario?run_id=' + encodeURIComponent(selectedRunId) + query;
      const response = await fetch(url, {cache:'no-store'});
      const data = await response.json();
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
      activeScenarioQuery = '';
      status.textContent = 'VS06-C2 sayısal hesap başarısız: ' + err.message;
      host.replaceChildren();
    } finally {
      button.disabled = false;
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
      wall_type:byId('c2WallType').value,
      unit_weight_kN_m3:byId('b1Gamma').value,
      unit_weight_min_kN_m3:byId('b1GammaMin').value,
      unit_weight_max_kN_m3:byId('b1GammaMax').value,
      opening_fraction:byId('b1Opening').value,
      low_load_ratio_cutoff:byId('b1Cutoff').value,
      shear_modulus_mpa:byId('b1Shear').value,
      R_base:byId('c2R').value
    };
  }
  async function calculateB1(){
    const status=byId('b1Status'),host=byId('b1Result'),btn=byId('b1Calculate');
    const a=byId('b1GeometryFile').files[0],b=byId('b1WallFile').files[0];
    if(!a||!b){status.textContent='B1_GEOMETRY ve LC_WDL_OBJECT JSON kaynaklarının ikisini de seçin.';return;}
    if(a.size+b.size>6*1024*1024){
      status.textContent='B1 kaynakları toplamı 6 MB sınırını geçiyor; güvenli yükleme yapılamadı.';return;
    }
    btn.disabled=true;
    byId('b1Json').disabled=true;
    byId('b1Html').disabled=true;
    b1Result=null;host.replaceChildren();
    status.textContent='Gerçek kaynaklar X/Y eleman, LC_WDL ve B1 kuralına eşleniyor…';
    try{
      const [geometry,wall_loads]=await Promise.all([a.text(),b.text()]);
      const payload={geometry:JSON.parse(geometry),wall_loads:JSON.parse(wall_loads),
                     options:b1CurrentOptions()};
      const response=await fetch('/api/vs06-b1-preview',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify(payload),cache:'no-store'
      });
      const body=await response.json();
      if(!response.ok)throw new Error(body.error||'B1_HTTP_'+response.status);
      if(!body.result||!body.html||body.result.formal_compliance!=='NOT_PROVEN'
         ||body.result.b1_numerical?.formal_compliance!=='NOT_PROVEN'){
        throw new Error('B1_SOURCE_RESULT_CONTRACT_INVALID');
      }
      b1Result=body;
      const r=body.result,number=r.b1_numerical;
      status.textContent='B1 X/Y: '+r.source_candidate_wall_beams+' LC_WDL kiriş, '+
        r.source_wall_load_rows+' gerçek atama; ηci,min='+number.eta_ci_min+
        ' · '+number.numeric_condition+' · resmî uygunluk NOT_PROVEN.';
      host.append(make('p','TBDY Tablo 3.6 · 3.6.2.3 · Aw + Ag + 0.15Ak. Ak yükten tuğla kalınlığı ve boşluk senaryosuyla tahmin edilmiştir.','muted small'));
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
    }catch(err){
      b1Result=null;status.textContent='B1 sayısal kaynak hesabı reddedildi: '+err.message;
      host.replaceChildren();
    }finally{
      btn.disabled=false;
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
  byId('b1Calculate')?.addEventListener('click',calculateB1);
  byId('b1Json')?.addEventListener('click',()=>{
    if(b1Result)b1Download('B1_SOURCE_NUMERIC.json',
      JSON.stringify(b1Result.result,null,2)+'\n','application/json;charset=utf-8',false);
  });
  byId('b1Html')?.addEventListener('click',()=>{
    if(b1Result)b1Download('B1_SOURCE_NUMERIC.html',
      b1Result.html,'text/html;charset=utf-8',true);
  });
  window.renderQuickChecksForTab = tab => {renderQuick(latest, tab);renderExtras(tab);};
  byId('runAllBtn')?.addEventListener('click', runSuite);
  loadRegistry();
  loadQuickHistory();
})();
