/* Presentation of one explicitly selected offline bank. No engineering arithmetic. */
(() => {
  'use strict';
  const el = id => document.getElementById(id);
  const run = el('columnRun'), member = el('columnMember'), loadCase = el('columnCase');
  const view = el('columnView');
  const labels = {
    STATIC_LINEAR_ADD:'Statik Linear Add', RESPONSE_SPECTRUM_LINEAR_ADD:'Spektral katkılı Linear Add',
    ENVELOPE:'Zarf', STATIC_NESTED_UNVERIFIED:'İç içe statik · doğrulanmadı',
    DEFINITION_UNRESOLVED:'Tanım çözümlenemedi', NON_LINEAR_ADD_ROUTE:'Diğer birleşim işlemi',
    OTHER_ANALYSIS_CASE:'Diğer analiz türü', UNIQUE_STATIC_SOURCE_LINK:'Tekil statik kaynak bağı',
    MULTIPLE_NATIVE_STATES:'Birden fazla kuvvet durumu', AMBIGUOUS_DESIGN_STATION:'Çift tasarım istasyonu',
    EXACT_NATIVE_STATION_NOT_FOUND:'Kesin istasyon eşleşmesi yok', SOURCE_REFERENCE_ONLY:'Yalnız kaynak referansı',
    DESIGN_MEMBER_CONTEXT_UNRESOLVED:'Kolon/kesit kimliği uyuşmuyor', COMBINATION_NOT_DEFINED:'Birleşim tanımı yok',
    DESIGN_STATION_INVALID:'İstasyon geçersiz'
  };
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
                      'columnReplay', 'columnCoverage', 'columnGaps', 'columnPage',
                      'columnDemandSummary', 'columnDemandRoutes', 'columnUnits']) el(id).replaceChildren();
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
    const selectedView = view.value || 'native';
    if (selectedView !== 'native') params.set('view', selectedView);
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
      const chain = report.demand_chain;
      if (chain) {
        if (chain.source_run_id !== selected || chain.source_archive_sha256 !== report.source_archive_sha256 ||
            chain.design_demand_authority !== 'DENIED') throw new Error('Talep görünümü başka bir kaynağa ait.');
        const d = chain.design_summary;
        el('columnDemandSummary').append(text('p', `${chain.combination_count} birleşim · ${chain.static_candidate_count} statik kaynak adayı · ` +
          `${d.row_count} tasarım özeti satırı · ${d.unique_static_links} tekil statik kaynak bağı`));
        el('columnDemandSummary').append(text('p', 'Bunlar analiz kaynaklarıdır; tasarım birleşimi seçimi, analiz mertebesi ve kapasite kabulü henüz doğrulanmadı.', 'micro'));
        el('columnDemandRoutes').append(table([['combination','Birleşim'],['label','Sınıf'],
          ['static_candidate_count','Statik aday'],['case_names','Kaynak vakalar'],['reason','Açık neden']],
          chain.combinations.map(r => ({...r,label:labels[r.classification] || r.classification}))));
        el('columnDemandRoutes').append(text('p', `${d.ambiguous_design_station_rows} çift istasyon kaydı; ` +
          `${d.references_without_exact_station} referansta kesin istasyon eşleşmesi yok. ` +
          'ETABS PMM oranındaki boş hücreler boş kalır. VMaj/VMin, V2/V3 olarak kendiliğinden eşlenmez.', 'micro'));
        if (d.reason) el('columnDemandRoutes').append(text('p', d.reason, 'micro'));
      }
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
      const page = selectedView === 'native' ? report.force_page : report.demand_page;
      if (!page || (selectedView !== 'native' && page.view !== selectedView)) throw new Error('İstenen talep görünümü bulunamadı.');
      total = page.total; offset = page.offset;
      const identity = [['Obj','Kolon'], ['Elm','Analiz elemanı'], ['ObjSta','Nesne istasyonu'], ['ElmSta','Eleman istasyonu'],
        ['LoadCase','Vaka / birleşim'], ['StepType','Adım'], ['StepNum','No']];
      if (selectedView === 'native') {
        el('columnUnits').textContent = 'Native işaretler korunur. Kuvvetler kN, momentler kN·m, istasyonlar m.';
        el('columnForces').append(table([...identity,...['P','V2','V3','T','M2','M3'].map(c => [c,c])], page.rows));
      } else if (selectedView === 'static') {
        el('columnUnits').textContent = 'N basınç pozitif = −P; çekme negatif kalır. Kuvvetler kN, momentler kN·cm, istasyonlar m; CSI yerel 2–3 eksenleri. Analiz mertebesi doğrulanmadı.';
        el('columnForces').append(table([...identity,['N_compression_kN','N (basınç +)'], ['V2_kN','V2'],
          ['V3_kN','V3'],['T_kNcm','T'],['M2_kNcm','M2'],['M3_kNcm','M3']],
          page.rows.map(r => ({...r.native_key,...r.domain_values}))));
      } else {
        el('columnUnits').textContent = 'ETABS tasarım özetindeki referanslar. Yuvarlanmış veya çift istasyonlardan tekil kuvvet seçilmez; bu görünüm PMM/kesme uygunluğu değildir.';
        const rows = page.rows.map(r => {
          const refs = Object.fromEntries(r.references.map(ref => [ref.role, ref]));
          const link = role => labels[refs[role]?.status] || refs[role]?.status;
          return {...r.native_design_row, pmmLink:link('PMM'), majorLink:link('MAJOR_SHEAR'), minorLink:link('MINOR_SHEAR')};
        });
        el('columnForces').append(table([['UniqueName','Kolon'],['Station','İstasyon (m)'],['DesignSect','Tasarım kesiti'],
          ['PMMCombo','PMM birleşimi'],['pmmLink','Kaynak bağı'],['PMMRatio','ETABS PMM oranı'],
          ['VMajCombo','Büyük yön kesme'],['majorLink','Kaynak bağı'],['VMinCombo','Küçük yön kesme'],['minorLink','Kaynak bağı']], rows));
      }
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
  for (const chooser of [member, loadCase, view]) chooser.addEventListener('change', () => { offset = 0; load(); });
  el('columnPrevious').addEventListener('click', () => { offset = Math.max(0, offset - 200); load(); });
  el('columnNext').addEventListener('click', () => { if (offset + 200 < total) { offset += 200; load(); } });
})();
