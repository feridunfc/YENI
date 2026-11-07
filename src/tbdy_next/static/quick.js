/* VS02: project-owned check tree and combined, bounded ETABS quick-screening UI. */
(() => {
  'use strict';
  let definitions = [];
  let latest = null;
  const nav = document.getElementById('nav');
  const byId = id => document.getElementById(id);
  const exportActions = document.createElement('div');
  exportActions.className = 'actions';
  exportActions.id = 'quickExportActions';
  const exportTitle = document.createElement('span');
  exportTitle.className = 'muted small';
  exportTitle.textContent = 'Tam rapor / JSON: önce beş kontrolü çalıştırın.';
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
    exportTitle.textContent = 'Kayıtlı beş kontrolün tamamı: kaynak veriler + tüm eleman satırları.';
  }
  jsonButton.disabled = true;
  printButton.disabled = true;
  chooseRun.addEventListener('change', () => {
    selectedRunId = chooseRun.value;
    const chosen = cachedHistory.find(r => r.run_id === selectedRunId);
    if (chosen) {
      useReport(chosen.geometry);
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
    } catch (error) {
      byId('quickStatus').textContent = 'Kontrol ağacı yüklenemedi: ' + error.message;
    }
  }
  function useReport(report) {
    latest = report;
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
        useReport(first.geometry);
        setExportRun(first.run_id);
        byId('quickStatus').textContent = `Son canlı tarama: ${first.model_name || 'ETABS'} · ${first.captured_at_utc}`;
      }
    } catch (error) {
      byId('quickStatus').textContent = 'Geçmiş kontrol kaydı okunamadı: ' + error.message;
    }
  }
  async function runSuite() {
    const button = byId('quickSuiteBtn');
    const status = byId('quickStatus');
    const modal = byId('liveCase').value.trim();
    if (!modal) {status.textContent = 'Modal vaka zorunludur.'; return;}
    button.disabled = true; status.textContent = 'ETABS modal ve altı geometri tablosu alınıyor…';
    try {
      const response = await fetch('/api/live-suite?case=' + encodeURIComponent(modal), {method:'POST',cache:'no-store'});
      const body = await response.json();
      if (!response.ok) throw new Error(body.result?.reason || body.reason || `HTTP ${response.status}`);
      if (typeof showResult === 'function') showResult('Canlı ETABS · 5 kontrol', body);
      if (typeof window.showModalFullTable === 'function') window.showModalFullTable(body.run_id);
      useReport(body.geometry);
      setExportRun(body.run_id, `${body.model_name || 'ETABS'} · yeni canlı çalışma`);
      byId('step1').textContent = `LIVE_ETABS · ${body.source_rows} modal satır`;
      byId('step2').textContent = body.geometry?.status || 'Şema bekleniyor';
      byId('step3').textContent = body.result.status;
      status.textContent = `Model: ${body.model_name} · Modal: ${body.result.status} · Geometri: ${body.geometry?.status}`;
      await loadRuns();
      // Calling refreshModalHistory would overwrite the newly selected run's UI;
      // the same run is already in the receipt history and can be refreshed there.
    } catch (error) {
      status.textContent = 'Hızlı tarama çalıştırılamadı: ' + error.message;
      status.className = 'live-status bad';
    } finally {button.disabled = false;}
  }
  window.renderQuickChecksForTab = tab => renderQuick(latest, tab);
  byId('quickSuiteBtn')?.addEventListener('click', runSuite);
  loadRegistry();
  loadQuickHistory();
})();
