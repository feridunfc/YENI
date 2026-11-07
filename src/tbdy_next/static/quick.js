/* VS02: project-owned check tree and combined, bounded ETABS quick-screening UI. */
(() => {
  'use strict';
  let definitions = [];
  let latest = null;
  let latestExtra = null;
  let latestVs04 = null;
  let latestVs04Numerics = null;
  let latestVs04Readiness = null;
  const nav = document.getElementById('nav');
  const byId = id => document.getElementById(id);
  const exportActions = document.createElement('div');
  exportActions.className = 'actions';
  exportActions.id = 'quickExportActions';
  const exportTitle = document.createElement('span');
  exportTitle.className = 'muted small';
  exportTitle.textContent = 'Tam rapor / JSON: ETABS'tan oku ve hesapla.';
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
    jsonButton.disabled = false;
    printButton.disabled = false;
    exportTitle.textContent = 'Kayıtlı kontrollerin tamamı: kaynak veriler + tüm eleman satırları.';
  }
  jsonButton.disabled = true;
  printButton.disabled = true;
  chooseRun.addEventListener('change', () => {
    selectedRunId = chooseRun.value;
    const chosen = cachedHistory.find(r => r.run_id === selectedRunId);
    if (chosen) {
      useReport(chosen.geometry, chosen.extra_checks, chosen.vs04_schema, chosen.vs04_numerics, chosen.vs04_readiness);
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
    window.location.assign('/api/export-checks?run_id=' + encodeURIComponent(selectedRunId));
  });
  printButton.addEventListener('click', () => {
    if (!selectedRunId) return;
    window.open('/report/print?run_id=' + encodeURIComponent(selectedRunId), '_blank', 'noopener');
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
      const details = make('details'); details.open = check.unmet_count > 0;
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
  function useReport(report, extra, vs04, vs04Numerics, vs04Readiness) {
    latest = report;
    latestExtra = extra || null;
    latestVs04 = vs04 || null;
    latestVs04Numerics = vs04Numerics || null;
    latestVs04Readiness = vs04Readiness || null;
    renderVs04();
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
        useReport(first.geometry, first.extra_checks, first.vs04_schema, first.vs04_numerics, first.vs04_readiness);
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
          || !body.vs04_readiness || !body.geometry || !body.extra_checks || !body.run_id) {
        throw new Error('INCOMPLETE_OR_UNVERIFIED_UNIFIED_RUN_CONTRACT');
      }
      if (typeof showResult === 'function') showResult('Canlı ETABS · Birleşik tarama', body);
      if (typeof window.showModalFullTable === 'function') window.showModalFullTable(body.run_id);
      useReport(body.geometry, body.extra_checks, body.vs04_schema,
                body.vs04_numerics, body.vs04_readiness);
      setExportRun(body.run_id, (body.model_name || 'ETABS') + ' · birleşik canlı çalışma');
      byId('step1').textContent = 'ETABS KAYNAĞI · ' + body.source_rows + ' modal satır';
      byId('step2').textContent = 'ŞEMA · ' + body.vs04_schema.status;
      byId('step3').textContent = 'HESAP · ' + body.result.status + ' / RELEASE NOT_READY';
      if (typeof setTree === 'function') {
        setTree('modeltree', [
          'ETABS: ' + (body.model_name || 'model adı gözlenmedi'),
          'Modal vaka: ' + modal,
          '3 analiz tablosu: ' + body.vs04_schema.captured_table_count + '/3',
          'Tek run_id: ' + body.run_id
        ]);
        const checks = [
          'Modal kütle: ' + body.result.status,
          ...(body.geometry.checks || []).map(c => c.check_id + ': ' + c.status),
          ...(body.extra_checks.checks || []).map(c => c.check_id + ': ' + c.status),
          'VS04 kaynak aritmetiği: ' + body.vs04_numerics.observed_component_count + '/5',
          'Normatif kanıt kapıları: ' + body.vs04_readiness.proven_check_count
            + '/' + body.vs04_readiness.expected_check_count,
          'Yönetmelik uygunluğu: NOT_PROVEN',
          'ENGINEERING RELEASE: NOT_READY'
        ];
        setTree('resulttree', checks);
      }
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
  window.renderQuickChecksForTab = tab => {renderQuick(latest, tab);renderExtras(tab);};
  byId('runAllBtn')?.addEventListener('click', runSuite);
  loadRegistry();
  loadQuickHistory();
})();
