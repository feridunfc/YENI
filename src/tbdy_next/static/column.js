/* Presentation of one explicitly selected offline bank. No engineering arithmetic. */
(() => {
  'use strict';
  const el = id => document.getElementById(id);
  const run = el('columnRun'), member = el('columnMember'), loadCase = el('columnCase');
  let epoch = 0, historyEpoch = 0, opened = false, offset = 0, total = 0;
  const text = (tag, value, css) => {
    const node = document.createElement(tag); node.textContent = String(value ?? '—');
    if (css) node.className = css;
    return node;
  };
  const show = value => Array.isArray(value) ? value.join(', ') : String(value ?? '—');
  function table(columns, rows) {
    const node = document.createElement('table'); node.className = 'modal-source-table';
    const head = document.createElement('thead'), header = document.createElement('tr');
    columns.forEach(([, label]) => header.append(text('th', label))); head.append(header);
    const body = document.createElement('tbody');
    rows.forEach(row => {
      const tr = document.createElement('tr');
      columns.forEach(([key]) => tr.append(text('td', show(row[key])))); body.append(tr);
    });
    node.append(head, body); return node;
  }
  function options(target, values, placeholder) {
    target.replaceChildren();
    const first = text('option', placeholder); first.value = ''; target.append(first);
    values.forEach(([value, label]) => { const option = text('option', label); option.value = value; target.append(option); });
    target.value = '';
  }
  function clearResult() {
    for (const id of ['columnSummary', 'columnExports', 'columnContext', 'columnForces',
                      'columnReplay', 'columnCoverage', 'columnGaps', 'columnPage']) el(id).replaceChildren();
    el('columnPrevious').disabled = true; el('columnNext').disabled = true;
  }
  async function get(url) {
    const response = await fetch(url, {cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Arşiv doğrulanamadı');
    return data;
  }
  async function load(resetFilters = false) {
    const ticket = ++epoch, selected = run.value;
    clearResult();
    if (resetFilters) {
      offset = 0; options(member, [], 'Tüm kolonlar'); options(loadCase, [], 'Tüm çıktılar');
    }
    if (!selected) { el('columnStatus').textContent = 'Kolon arşivi seçilmedi.'; return; }
    const params = new URLSearchParams({run_id:selected, offset:String(offset)});
    if (member.value) params.set('member', member.value);
    if (loadCase.value) params.set('case', loadCase.value);
    el('columnStatus').textContent = 'Arşiv doğrulanıyor…';
    try {
      const report = await get('/api/column-bank?' + params);
      if (ticket !== epoch || selected !== run.value) return;
      if (report.run_id !== selected || report.formal_compliance !== 'NOT_PROVEN' || report.design_demand_authority !== 'DENIED') {
        throw new Error('Arşiv kimliği veya kapsamı beklenen sözleşmeyle eşleşmiyor.');
      }
      if (resetFilters) {
        options(member, report.members.map(m => [m.frame_name,
          m.frame_name + ' · ' + (m.context?.frame?.story_label || 'Kat belirsiz')]), 'Tüm kolonlar');
        options(loadCase, report.case_coverage.map(c => [c.name, c.name + (c.row_count ? '' : ' · veri yok')]), 'Tüm çıktılar');
      }
      el('columnStatus').textContent = selected + ' · NOT_PROVEN / NOT_READY';
      el('columnSummary').append(text('p', `${report.observed_column_count}/${report.selected_column_count} seçili kolon · ${report.force_row_count} kuvvet satırı · ${report.recorded_output_count} kayıtlı vaka/birleşim`));
      el('columnSummary').append(text('p', 'Kaynak SHA-256: ' + report.source_archive_sha256, 'micro'));
      for (const [label, url] of [
        ['HTML hesap raporu', '/report/column-bank?'],
        ['Tam JSON', '/api/export-column-bank?format=json&'],
        ['SQLite kuvvet bankası', '/api/export-column-bank?format=sqlite&']]) {
        const link = text('a', label); link.href = url + 'run_id=' + encodeURIComponent(selected);
        link.target = '_blank'; link.rel = 'noopener'; el('columnExports').append(link);
      }
      const chosen = report.members.find(m => m.frame_name === member.value);
      if (chosen) {
        const ctx = chosen.context || {}, g = chosen.station_geometry || {};
        el('columnContext').append(text('p', `${ctx.frame?.section_assigned || 'Kesit belirsiz'} · ` +
          `b2/b3: ${show(ctx.geometry?.T2_cm)}/${show(ctx.geometry?.T3_cm)} cm · Fc/Fy: ${show(ctx.material?.fc_MPa)}/${show(ctx.material?.fy_MPa)} MPa · ` +
          `I–J: ${show(g.object_i_j_length_m)} m · J offset: ${show(g.offset_j_m)} m · son çıktı J düğümünde: ${show(g.last_station_is_joint_j)}`));
        el('columnContext').append(text('p', 'Çıktı yüzleri arası mesafe TS500 serbest/etkili boy değildir. Model donatı ayarı gerçek veya seçilmiş donatı kafesi değildir.', 'micro'));
        if (chosen.reason_codes.length) el('columnContext').append(text('p', chosen.reason_codes.join(' · '), 'warn'));
      }
      const page = report.force_page; total = page.total; offset = page.offset;
      el('columnForces').append(table([
        ['Obj','Kolon'], ['Elm','Analiz elemanı'], ['ObjSta','Nesne istasyonu'], ['ElmSta','Eleman istasyonu'],
        ['LoadCase','Vaka / birleşim'], ['StepType','Adım'], ['StepNum','No'],
        ...['P','V2','V3','T','M2','M3'].map(c => [c,c])], page.rows));
      el('columnPage').textContent = total ? `${offset + 1}–${Math.min(offset + page.limit,total)} / ${total}` : 'Bu seçim için kaynak satırı yok.';
      el('columnPrevious').disabled = offset === 0;
      el('columnNext').disabled = offset + page.limit >= total;
      const replay = report.static_replay;
      el('columnReplay').append(text('p', `${replay.matched_rows} eşleşen statik satır · ${replay.scalar_comparisons} skaler karşılaştırma · en büyük |Δ|: ${replay.maximum_absolute_difference}`));
      el('columnReplay').append(text('p', 'Bu sonuç kaynak aritmetiğini doğrular. RS, zarf ve iç içe birleşimler bu hesap yoluyla tasarım vektörüne dönüştürülmez.', 'micro'));
      el('columnReplay').append(table([['combination','Birleşim'],['status','Sayısal kaynak'],['matched_rows','Eşleşen'],
        ['mismatched_rows','Farklı'],['unresolved_rows','Çözümlenemeyen'],['reason','Neden']], replay.combinations));
      el('columnCoverage').append(table([['name','Vaka / birleşim'],['row_count','Satır'],['members_with_rows','Verili kolon'],
        ['expected_members','Beklenen'],['step_types','Adım'],['step_numbers','Adım / mod no'],['missing_members','Eksik kolonlar']], report.case_coverage));
      el('columnGaps').append(table([['topic','İş paketi'],['available','Kaynak'],['remaining','Tamamlanacak bağ']], report.engineering_gaps));
    } catch (error) {
      if (ticket !== epoch || selected !== run.value) return;
      clearResult(); el('columnStatus').textContent = 'Arşiv gösterilemedi: ' + error.message;
    }
  }
  async function refresh() {
    const ticket = ++historyEpoch; ++epoch; clearResult();
    options(run, [], 'Arşivler okunuyor…'); options(member, [], 'Tüm kolonlar'); options(loadCase, [], 'Tüm çıktılar');
    run.disabled = true;
    try {
      const data = await get('/api/column-history');
      if (ticket !== historyEpoch) return;
      options(run, data.runs.map(r => [r.run_id, `${r.run_id} · ${r.force_row_count} satır`]), 'Arşiv seçin');
      el('columnStatus').textContent = data.runs.length ? 'İncelenecek kolon arşivini seçin.' :
        'Henüz içe aktarılmış kolon arşivi yok. Çevrimdışı ZIP içe aktarıldığında burada görünür.';
    } catch (error) {
      if (ticket === historyEpoch) el('columnStatus').textContent = 'Arşiv listesi okunamadı: ' + error.message;
    } finally { if (ticket === historyEpoch) run.disabled = false; }
  }
  window.openColumnBank = () => { if (!opened) { opened = true; refresh(); } };
  el('columnRefresh').addEventListener('click', refresh);
  run.addEventListener('change', () => load(true));
  for (const chooser of [member, loadCase]) chooser.addEventListener('change', () => { offset = 0; load(); });
  el('columnPrevious').addEventListener('click', () => { offset = Math.max(0, offset - 200); load(); });
  el('columnNext').addEventListener('click', () => { if (offset + 200 < total) { offset += 200; load(); } });
})();
