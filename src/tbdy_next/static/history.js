/* VS01: show already-verified local CLI receipts; no ETABS or network beyond localhost. */
(() => {
  'use strict';
  const statusBox = document.getElementById('saved-modal-body');
  const historyBox = document.getElementById('saved-modal-history');
  const refreshButton = document.getElementById('refreshSaved');
  if (!statusBox || !historyBox || !refreshButton) return;

  function node(tag, content, className) {
    const element = document.createElement(tag);
    if (content !== undefined) element.textContent = String(content);
    if (className) element.className = className;
    return element;
  }
  function percent(ratio) {
    const number = Number(ratio);
    return Number.isFinite(number) ? `${(number * 100).toFixed(2)}%` : '—';
  }
  function progress(label, ratio) {
    const col = node('div');
    const top = node('div', undefined, 'statline');
    top.append(node('span', label), node('strong', percent(ratio)));
    const track = node('div');
    track.style.cssText = 'height:12px;background:#e8edf3;border-radius:8px;overflow:hidden;margin-top:8px';
    const bar = node('div');
    const fraction = Number(ratio);
    const valid = Number.isFinite(fraction) && fraction >= 0 && fraction <= 1;
    bar.style.width = valid ? `${fraction * 100}%` : '0%';
    bar.style.height = '100%';
    bar.style.background = valid && fraction >= 0.95 ? 'var(--ok)' : 'var(--warn)';
    track.append(bar);
    col.append(top, track);
    return col;
  }
  function info(container, key, value) {
    const line = node('div', undefined, 'statline');
    line.append(node('span', key), node('strong', value));
    container.append(line);
  }
  let tableRequestVersion = 0;
  async function showModalFullTable(runId) {
    const host = document.getElementById('result');
    if (!host || !runId) return;
    const version = ++tableRequestVersion;
    const divider = node('hr', undefined, 'modal-table-divider');
    const section = node('section', undefined, 'modal-table-section');
    section.append(node('p', 'Loading the full modal table…', 'muted small'));
    host.append(divider, section);
    try {
      const response = await fetch('/api/modal-table?run_id=' + encodeURIComponent(runId), {cache: 'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const record = payload.table;
      if (!record || !Array.isArray(record.fields) || !Array.isArray(record.rows)
          || record.rows.length !== record.row_count) throw new Error('Incomplete or inconsistent table');
      if (version !== tableRequestVersion || !section.isConnected) return;
      const title = node('div', undefined, 'modal-table-title');
      title.append(node('h3', 'Full ETABS modal source table'),
                   node('strong', `${record.row_count} rows · ${record.fields.length} columns`, 'small'));
      const caption = node('p', `${record.table_key} · Case: ${record.case} · ${record.source_mode}. `
        + 'All recorded rows and original columns. Modal ratios were evaluated for the selected case.', 'muted small');
      const scroll = node('div', undefined, 'modal-table-scroll');
      scroll.setAttribute('role', 'region');
      scroll.setAttribute('aria-label', 'Full modal source table');
      scroll.tabIndex = 0;
      const table = node('table', undefined, 'modal-source-table');
      const thead = node('thead');
      const header = node('tr');
      for (const field of record.fields) {
        const cell = node('th', field);
        cell.setAttribute('scope', 'col');
        header.append(cell);
      }
      thead.append(header);
      const tbody = node('tbody');
      for (const row of record.rows) {
        const line = node('tr');
        for (const field of record.fields) line.append(node('td', row[field] ?? ''));
        tbody.append(line);
      }
      table.append(thead, tbody);
      scroll.append(table);
      section.replaceChildren(title, caption, scroll);
    } catch (error) {
      if (version === tableRequestVersion && section.isConnected) {
        section.replaceChildren(node('p', `Could not display the full source table: ${error.message}`, 'bad'));
      }
    }
  }
  window.showModalFullTable = showModalFullTable;
  function showRun(entry, selectShared = true) {
    const result = entry.result || {};
    const source = entry.source_mode === 'LIVE_ETABS' ? 'LIVE ETABS' : entry.source_mode === 'OFFLINE_ETABS' ? 'OFFLINE ETABS' : 'SYNTHETIC';
    const label = result.status === 'MEETS_NUMERICAL_CRITERION' ? 'NUMERICAL CRITERION MET' : 'NUMERICAL CRITERION NOT MET';
    const heading = node('h3', `${label} · ${source}`, result.status === 'MEETS_NUMERICAL_CRITERION' ? 'good' : 'bad');
    const context = node('p', `Model: ${entry.model_name || 'not specified in the source record'} · Case: ${entry.case} · Run: ${entry.run_id}`, 'muted small');
    const two = node('div', undefined, 'twocol');
    two.append(progress('X total effective mass', result.sum_ux), progress('Y total effective mass', result.sum_uy));
    const details = node('div');
    info(details, 'Rows read from the full modal table', entry.raw_row_count ?? '—');
    info(details, 'Modes in the selected case', entry.case_row_count ?? '—');
    info(details, 'Governing mode count', result.governing_mode_count ?? '—');
    info(details, 'Required threshold', percent(result.required_ratio));
    info(details, 'X modes contributing >3%', (result.significant_modes_x || []).join(', ') || 'None');
    info(details, 'Y modes contributing >3%', (result.significant_modes_y || []).join(', ') || 'None');
    info(details, 'Engineering release', 'NOT_READY · 95% mass subcondition only');
    const stamp = node('p', `Result time: ${entry.captured_at_utc} · Local source SHA-256: ${String(entry.input_sha256 || '').slice(0,16)}…`, 'muted small');
    const note = node('p', 'Source, schema, and result receipts were verified. The result covers the modal mass subcondition of TBDY.', 'muted small');
    statusBox.replaceChildren(heading, context, two, details, stamp, note);

    // The combined UI owns the selected run. A background history refresh
    // must not replace its sidebars or leave checks from another run visible.
    if (typeof window.selectSavedEngineeringRun === 'function') {
      window.selectSavedEngineeringRun(entry, selectShared);
      return;
    }

    // Also populate the original result surface / result tree on initial load.
    if (typeof showResult === 'function') showResult('Saved modal calculation', {result});
    showModalFullTable(entry.run_id);
    document.getElementById('step1').textContent = `${source} · ${entry.raw_row_count} rows`;
    document.getElementById('step2').textContent = `SCHEMA_VALID · ${entry.case_row_count} mod`;
    document.getElementById('step3').textContent = result.status || 'Waiting for calculations';
    if (typeof setTree === 'function') {
      setTree('modeltree', [entry.model_name || 'Modal source', `Source: ${source}`, `Case: ${entry.case}`, `Rows: ${entry.raw_row_count}`]);
      setTree('resulttree', ['VS01 · Effective modal mass', `X: ${percent(result.sum_ux)}`, `Y: ${percent(result.sum_uy)}`, `Governing mode: ${result.governing_mode_count ?? '—'}`, `Mode count: ${entry.case_row_count}`, `Numerical status: ${label}`, 'Release: NOT_READY']);
    }
  }
  async function refresh() {
    refreshButton.disabled = true;
    try {
      const response = await fetch('/api/modal-history', {cache: 'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const runs = Array.isArray(payload.runs) ? payload.runs : [];
      if (!runs.length) {
        statusBox.replaceChildren(node('p', 'No verified modal runs found. Check that the CLI wrote to .receipts and that the server is running from the same project.', 'muted'));
        historyBox.replaceChildren();
        return;
      }
      const selected = runs.find(r => r.source_mode === 'LIVE_ETABS') || runs[0];
      showRun(selected, false);
      historyBox.replaceChildren(node('span', 'Previous runs:', 'muted small'));
      for (const entry of runs.slice(0, 12)) {
        const button = node('button', `${entry.source_mode === 'LIVE_ETABS' ? 'ETABS' : 'TEST'} · ${entry.captured_at_utc.slice(0,16).replace('T',' ')} · ${entry.case}`, 'go');
        button.type = 'button';
        button.addEventListener('click', () => showRun(entry));
        historyBox.append(button);
      }
    } catch (error) {
      statusBox.replaceChildren(node('p', `Could not load saved runs:${error.message}`, 'bad'));
    } finally {
      refreshButton.disabled = false;
    }
  }
  window.refreshModalHistory=refresh;
  refreshButton.addEventListener('click', refresh);
  refresh();
})();
