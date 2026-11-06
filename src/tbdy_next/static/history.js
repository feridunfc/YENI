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
    return Number.isFinite(number) ? `${(number * 100).toFixed(2).replace('.', ',')}%` : '—';
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
  function showRun(entry) {
    const result = entry.result || {};
    const source = entry.source_mode === 'LIVE_ETABS' ? 'CANLI ETABS' : entry.source_mode === 'OFFLINE_ETABS' ? 'OFFLINE ETABS' : 'SENTETİK';
    const label = result.status === 'MEETS_NUMERICAL_CRITERION' ? 'SAYISAL KOŞUL SAĞLANDI' : 'SAYISAL KOŞUL SAĞLANMADI';
    const heading = node('h3', `${label} · ${source}`, result.status === 'MEETS_NUMERICAL_CRITERION' ? 'good' : 'bad');
    const context = node('p', `Model: ${entry.model_name || 'kaynak kaydında belirtilmemiş'} · Vaka: ${entry.case} · Çalışma: ${entry.run_id}`, 'muted small');
    const two = node('div', undefined, 'twocol');
    two.append(progress('X yönü toplam etkin kütle', result.sum_ux), progress('Y yönü toplam etkin kütle', result.sum_uy));
    const details = node('div');
    info(details, 'Okunan tam modal tablo satırı', entry.raw_row_count ?? '—');
    info(details, 'Seçilen vakadaki mod sayısı', entry.case_row_count ?? '—');
    info(details, 'Yönetici mod sayısı', result.governing_mode_count ?? '—');
    info(details, 'Gerekli sınır', percent(result.required_ratio));
    info(details, 'X yönü >%3 katkılı modlar', (result.significant_modes_x || []).join(', ') || 'Yok');
    info(details, 'Y yönü >%3 katkılı modlar', (result.significant_modes_y || []).join(', ') || 'Yok');
    info(details, 'Mühendislik release', 'NOT_READY — yalnız %95 sayısal alt kontrol');
    const stamp = node('p', `Sonuç tarihi: ${entry.captured_at_utc} · Yerel kaynak SHA-256: ${String(entry.input_sha256 || '').slice(0,16)}…`, 'muted small');
    const note = node('p', 'Kaynak, şema ve sonuç kayıtları tekrar doğrulandı. Bu sonuç tam TBDY deprem tasarımı kabulü değildir.', 'muted small');
    statusBox.replaceChildren(heading, context, two, details, stamp, note);

    // Also populate the original result surface / result tree on initial load.
    if (typeof showResult === 'function') showResult('Kaydedilmiş modal hesap', {result});
    document.getElementById('step1').textContent = `${source} · ${entry.raw_row_count} satır`;
    document.getElementById('step2').textContent = `SCHEMA_VALID · ${entry.case_row_count} mod`;
    document.getElementById('step3').textContent = result.status || 'Hesap bekleniyor';
    if (typeof setTree === 'function') {
      setTree('modeltree', [entry.model_name || 'Modal kaynak', `Kaynak: ${source}`, `Vaka: ${entry.case}`, `Satır: ${entry.raw_row_count}`]);
      setTree('resulttree', ['VS01 · Etkin modal kütle', `X: ${percent(result.sum_ux)}`, `Y: ${percent(result.sum_uy)}`, `Yönetici mod: ${result.governing_mode_count ?? '—'}`, `Mod sayısı: ${entry.case_row_count}`, `Sayısal durum: ${label}`, 'Release: NOT_READY']);
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
        statusBox.replaceChildren(node('p', 'Henüz doğrulanmış modal hesap kaydı bulunamadı. CLI sonucunuzun .receipts klasörüne yazıldığından ve sunucunun aynı proje klasöründen açıldığından emin olun.', 'muted'));
        historyBox.replaceChildren();
        return;
      }
      const selected = runs.find(r => r.source_mode === 'LIVE_ETABS') || runs[0];
      showRun(selected);
      historyBox.replaceChildren(node('span', 'Önceki hesaplar:', 'muted small'));
      for (const entry of runs.slice(0, 12)) {
        const button = node('button', `${entry.source_mode === 'LIVE_ETABS' ? 'ETABS' : 'TEST'} · ${entry.captured_at_utc.slice(0,16).replace('T',' ')} · ${entry.case}`, 'go');
        button.type = 'button';
        button.addEventListener('click', () => showRun(entry));
        historyBox.append(button);
      }
    } catch (error) {
      statusBox.replaceChildren(node('p', `Kayıtlar okunamadı: ${error.message}`, 'bad'));
    } finally {
      refreshButton.disabled = false;
    }
  }
  window.refreshModalHistory=refresh;
  refreshButton.addEventListener('click', refresh);
  refresh();
})();
