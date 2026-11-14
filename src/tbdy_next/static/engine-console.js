/* Client-only, bounded UI execution log. Does not write ETABS, receipts or network. */
(() => {
  'use strict';
  const host = document.getElementById('engineConsoleMessages');
  const clearButton = document.getElementById('engineConsoleClear');
  const LIMIT = 40;
  const LEVELS = new Set(['info', 'warn', 'error', 'success']);

  function log(level, stage, message) {
    if (!host) return;
    const kind = LEVELS.has(level) ? level : 'info';
    const step = String(stage == null ? 'ENGINE' : stage).replace(/\s+/g, ' ').slice(0, 45);
    // Display only a bounded status/exception string. Never log request bodies,
    // whole ETABS tables, user files or stack traces to the UI.
    const value = String(message == null ? '' : message).slice(0, 620);
    if (host.dataset.empty === 'true') {
      host.replaceChildren();
      host.dataset.empty = 'false';
    }
    const entry = document.createElement('li');
    entry.className = 'engine-console-entry engine-console-' + kind;
    const meta = document.createElement('span');
    meta.className = 'engine-console-meta';
    meta.textContent = new Date().toLocaleTimeString('tr-TR', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    }) + ' · ' + kind.toUpperCase() + ' · ' + step;
    const detail = document.createElement('span');
    detail.className = 'engine-console-message';
    detail.textContent = value;
    entry.append(meta, detail);
    host.prepend(entry);
    while (host.children.length > LIMIT) host.removeChild(host.lastElementChild);
    host.scrollTop = 0;
  }

  function clear() {
    if (!host) return;
    const empty = document.createElement('li');
    empty.className = 'engine-console-entry engine-console-empty';
    empty.textContent = 'Henüz işlem kaydı yok.';
    host.replaceChildren(empty);
    host.dataset.empty = 'true';
  }

  clearButton?.addEventListener('click', clear);
  window.engineConsole = Object.freeze({log, clear});

  // Surface unexpected application errors without printing traces or source data.
  window.addEventListener?.('unhandledrejection', event => {
    const reason = event.reason instanceof Error ? event.reason.message : 'Beklenmeyen asenkron hata';
    log('error', 'ARAYÜZ', reason);
  });
  window.addEventListener?.('error', event => {
    log('error', 'ARAYÜZ', event.message || 'Beklenmeyen arayüz hatası');
  });
})();
