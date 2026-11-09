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
    DESIGN_STATION_INVALID:'İstasyon geçersiz', N_COMPRESSION_MAX:'En büyük basınç', N_TENSION_MAX:'En büyük çekme',
    M2_ABS_MAX:'En büyük |M2|', M3_ABS_MAX:'En büyük |M3|', V2_ABS_MAX:'En büyük |V2|',
    V3_ABS_MAX:'En büyük |V3|', T_ABS_MAX:'En büyük |T|',
    REQUIRED_AREA_BOUNDS_CALCULATED:'Alan sınırları hesaplandı', NOT_PROVEN:'Doğrulanmadı',
    NUMERICAL_MATCH:'Kaynakla eşleşti', NUMERICAL_MISMATCH:'Kaynakla uyuşmuyor',
    BELOW_REFERENCE:'Referans altında', AT_OR_ABOVE_REFERENCE:'Referansı karşılıyor',
    NONCOMPRESSION_NOT_APPLICABLE:'Basınç değil', PROPOSED_GEOMETRY_CALCULATED:'Öneri geometrisi',
    WITHIN_SCENARIO_SURFACE:'Koşullu yüzey içinde', EXCEEDS_SCENARIO_SURFACE:'Koşullu yüzey aşılıyor',
    NUMERIC_UNRESOLVED:'Sayısal çözüm belirsiz', BLOCKED_INPUTS:'Girdi eksik',
    AXIAL_ONLY_SCENARIO:'Yalnız eksenel senaryo', OUTSIDE_SCENARIO_AXIAL_RANGE:'Eksenel senaryo sınırı aşılıyor',
    WITHIN_1_TO_4_PERCENT_REFERENCE:'%1–4 aralığında', OUTSIDE_1_TO_4_PERCENT_REFERENCE:'%1–4 aralığı dışında',
    ANGULAR_REFINEMENT_NOT_STABLE:'Açısal yakınsama yeterli değil', AGGREGATE_NOT_BOUND:'Agrega bilgisi bekleniyor',
    NEAR_NUMERICAL_SURFACE_BOUNDARY:'Sayısal sınır bandında; karar belirsiz',
    PROPOSED_TRANSVERSE_REFERENCES_CALCULATED:'Öneri sargı hesabı',
    SHEAR_REFERENCES_CALCULATED:'İki kesme senaryosu hesaplandı', SHEAR_REFERENCE_PARTIAL:'Kesme senaryosu kısmi',
    WITHIN_REFERENCE_RESISTANCE:'Referans dayanım içinde', EXCEEDS_REFERENCE_RESISTANCE:'Referans dayanımı aşıyor',
    OUTSIDE_CRACKING_FORMULA_DOMAIN:'Çekme durumu formül alanı dışında',
    ENCLOSED:'Kuşatılmış · eşmerkez senaryo', UNENCLOSED:'Kuşatılmamış · eşmerkez senaryo',
    JOINT_GEOMETRIC_REFERENCES_CALCULATED:'Geometrik referans hesaplandı',
    NO_RECORDED_BEAM_AT_NODE:'Düğümde kayıtlı kiriş yok',
    JOINT_OTHER_INCIDENT_FRAME_NOT_CLASSIFIED:'Sınıflandırılmamış bağlı çubuk',
    JOINT_INTERIOR_FRAME_CONNECTION_NOT_BOUND:'Çubuk içindeki bağlantı belirsiz',
    JOINT_COINCIDENT_DISTINCT_POINT_IDS:'Aynı koordinatta farklı düğümler',
    EQ71_BASELINE_REFERENCES_CALCULATED:'Denk. 7.1 esaslı sargı referansı',
    SAME_CASE_SOURCE_LINKED:'Aynı birleşimde kaynaklar bağlı', PARTIAL_SOURCE_LINK:'Kısmi kaynak bağı',
    RECORDED_PDELTA_STIFFNESS:'P-Delta rijitliği kaydı',
    RECORDED_NONLINEAR_CASE_UNRESOLVED:'Nonlinear Case kaydı · başlangıç esası belirsiz',
    RECORDED_STIFFNESS_SETTING:'Rijitlik ayarı kaydedilmiş'
  };
  let epoch = 0, historyEpoch = 0, opened = false, offset = 0, total = 0;
  const text = (tag, value, css) => {
    const node = document.createElement(tag); node.textContent = String(value ?? '—');
    if (css) node.className = css;
    return node;
  };
  const show = value => Array.isArray(value) ? value.join(', ') : String(value ?? '—');
  const rounded = value => typeof value === 'number' && Number.isFinite(value) ? Number(value.toPrecision(6)) : null;
  function cageDrawing(cage, layout = null) {
    const box = document.createElement('figure');
    const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
    const make = (tag,attrs) => {
      const node = document.createElementNS('http://www.w3.org/2000/svg',tag);
      for (const [key,value] of Object.entries(attrs)) node.setAttribute(key,String(value));
      svg.append(node); return node;
    };
    const w=cage.t3_mm,h=cage.t2_mm; // Native T3 is the local-2 extent.
    svg.setAttribute('viewBox',`${-w/2-60} ${-h/2-60} ${w+120} ${h+120}`);
    svg.setAttribute('width','190'); svg.setAttribute('height','190');
    svg.setAttribute('role','img'); svg.setAttribute('aria-label',cage.label+' öneri kesiti; yerel 2 sağa, yerel 3 yukarı');
    make('rect',{x:-w/2,y:-h/2,width:w,height:h,fill:'#edf1f6',stroke:'#64748b','stroke-width':3});
    if (layout) for (const leg of layout.legs) {
      const [a,b] = leg.endpoints_mm;
      make('line',{x1:a[0],y1:-a[1],x2:b[0],y2:-b[1],stroke:'#34786b','stroke-width':leg.diameter_mm,
        'stroke-dasharray':leg.kind==='CROSSTIE' ? '12 6' : 'none'});
    }
    for (const bar of cage.bars) make('circle',{cx:bar.x2_mm,cy:-bar.x3_mm,r:bar.diameter_mm/2,fill:'#214e78'});
    box.append(svg,text('figcaption',`${cage.label} · As ${rounded(cage.as_cm2)} cm² · merkez örtüsü ${cage.center_offset_mm} mm`));
    if (layout) box.append(text('p','Etriye/çiroz eksen şeması; kancalar ve düşey yerleşim doğrulanmadı.','micro'));
    return box;
  }
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
    const selectedView = view.value || 'native';
    const sectionView = ['reinforcement','stiffness','cages','transverse','joints','joint-ties'].includes(selectedView);
    loadCase.disabled = sectionView;
    if (member.value) params.set('member', member.value);
    if (loadCase.value && !sectionView) params.set('case', loadCase.value);
    if (selectedView !== 'native') params.set('view', selectedView);
    el('columnStatus').textContent = selectedView === 'pmm' ? 'Koşullu PMM hesaplanıyor; ilk açılış biraz sürebilir…' : 'Arşiv doğrulanıyor…';
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
      const prechecks = report.column_prechecks;
      if (prechecks) {
        if (prechecks.source_run_id !== selected || prechecks.source_archive_sha256 !== report.source_archive_sha256 ||
            prechecks.source_demand_result_sha256 !== chain?.result_sha256 || prechecks.design_demand_authority !== 'DENIED') {
          throw new Error('Kolon ön hesabı seçili kuvvet zinciriyle eşleşmiyor.');
        }
        el('columnDemandSummary').append(text('p', `${prechecks.critical_selection.critical_state_count} kritik statik kayıt · ` +
          `${prechecks.reinforcement_bounds.calculated_member_count} kolonda boyuna donatı alan sınırı`));
      }
      const stability = report.column_stability;
      if (stability && (stability.source_run_id !== selected || stability.source_archive_sha256 !== report.source_archive_sha256 ||
          stability.source_demand_result_sha256 !== chain?.result_sha256 || stability.source_prechecks_result_sha256 !== prechecks?.result_sha256 ||
          stability.design_demand_authority !== 'DENIED' || stability.actual_second_order_applied !== false)) {
        throw new Error('Rijitlik hesabı seçili kolon kaynağıyla eşleşmiyor.');
      }
      const cages = report.column_cages, pmm = report.column_pmm;
      if (cages && (cages.source_run_id !== selected || cages.source_archive_sha256 !== report.source_archive_sha256 ||
          cages.source_demand_result_sha256 !== chain?.result_sha256 || cages.source_prechecks_result_sha256 !== prechecks?.result_sha256 ||
          cages.design_demand_authority !== 'DENIED' || cages.selected_design !== null)) {
        throw new Error('Donatı önerileri seçili kolon kaynağıyla eşleşmiyor.');
      }
      if (pmm && (pmm.source_run_id !== selected || pmm.source_archive_sha256 !== report.source_archive_sha256 ||
          pmm.source_demand_result_sha256 !== chain?.result_sha256 || pmm.source_cages_result_sha256 !== cages?.result_sha256 ||
          pmm.source_stability_result_sha256 !== stability?.result_sha256 || pmm.design_demand_authority !== 'DENIED' ||
          pmm.pmm_population_reduced !== false || pmm.actual_second_order_applied !== false ||
          pmm.minimum_eccentricity_applied !== false || pmm.selected_design !== null || pmm.formal_compliance !== 'NOT_PROVEN')) {
        throw new Error('PMM hesabının kaynak bağı veya koşullu kapsamı uyuşmuyor.');
      }
      const transverse = report.column_transverse, shear = report.column_shear;
      if (transverse && (transverse.source_run_id !== selected || transverse.source_archive_sha256 !== report.source_archive_sha256 ||
          transverse.source_demand_result_sha256 !== chain?.result_sha256 || transverse.source_cages_result_sha256 !== cages?.result_sha256 ||
          transverse.design_demand_authority !== 'DENIED' || transverse.formal_compliance !== 'NOT_PROVEN' || transverse.selected_design !== null ||
          transverse.proposal_policy?.physical_arrangement_proven !== false)) {
        throw new Error('Enine donatı önerisinin kaynak bağı veya koşullu kapsamı uyuşmuyor.');
      }
      if (shear && (shear.source_run_id !== selected || shear.source_archive_sha256 !== report.source_archive_sha256 ||
          shear.source_demand_result_sha256 !== chain?.result_sha256 || shear.source_cages_result_sha256 !== cages?.result_sha256 ||
          shear.source_transverse_result_sha256 !== transverse?.result_sha256 || shear.design_demand_authority !== 'DENIED' ||
          shear.formal_compliance !== 'NOT_PROVEN' || shear.selected_design !== null || shear.ve_status !== 'NOT_PROVEN' ||
          shear.source_population_reduced !== false || shear.actual_second_order_applied !== false || shear.vc_zero_gate?.required !== null)) {
        throw new Error('Kesme hesabının kaynak bağı veya koşullu kapsamı uyuşmuyor.');
      }
      const joints = report.column_joints;
      const kinematics = report.column_kinematics;
      if (kinematics && (kinematics.source_run_id !== selected || kinematics.source_archive_sha256 !== report.source_archive_sha256 ||
          kinematics.source_bank_result_sha256 !== report.result_sha256 || kinematics.source_demand_result_sha256 !== chain?.result_sha256 ||
          kinematics.source_joints_result_sha256 !== joints?.result_sha256 ||
          kinematics.axis_convention !== 'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3' ||
          kinematics.coordinate_contract !== 'ETABS_POINT_OBJECT_UX_UY_UZ_RX_RY_RZ_GLOBAL' ||
          kinematics.analysis_order !== 'NOT_PROVEN' || kinematics.analysis_generation_qualified !== false ||
          kinematics.actual_second_order_applied !== false || kinematics.cm !== null || kinematics.beta !== null ||
          kinematics.magnified_design_moments !== null || kinematics.design_demand_authority !== 'DENIED' ||
          kinematics.formal_compliance !== 'NOT_PROVEN' || kinematics.engineering_release !== 'NOT_READY')) {
        throw new Error('Kolon uç hareketlerinin kaynak bağı veya analiz kapsamı uyuşmuyor.');
      }
      for (const calculation of [stability,cages,pmm,transverse,shear]) {
        if (calculation && calculation.axis_convention !== 'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3') {
          throw new Error('Kesit eksen sözleşmesi eski veya belirsiz; güncel hesap gerekli.');
        }
      }
      if (joints && (joints.source_run_id !== selected || joints.source_archive_sha256 !== report.source_archive_sha256 ||
          joints.source_bank_result_sha256 !== report.result_sha256 || joints.source_demand_result_sha256 !== chain?.result_sha256 ||
          joints.source_cages_result_sha256 !== cages?.result_sha256 || joints.source_transverse_result_sha256 !== transverse?.result_sha256 ||
          joints.design_demand_authority !== 'DENIED' || joints.formal_compliance !== 'NOT_PROVEN' || joints.engineering_release !== 'NOT_READY' ||
          joints.ve_status !== 'NOT_PROVEN' || joints.scwb_status !== 'NOT_PROVEN' || joints.selected_design !== null ||
          joints.physical_geometry_proven !== false || joints.physical_joint_population_proven !== false ||
          joints.scenario !== 'CENTERLINE_AS_SECTION_CENTER_SCENARIO' ||
          joints.axis_convention !== 'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3')) {
        throw new Error('Birleşim hesabının kaynak bağı veya koşullu kapsamı uyuşmuyor.');
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
      if ((selectedView === 'critical' || selectedView === 'reinforcement') && !prechecks) throw new Error('Kolon ön hesabı bulunamadı.');
      if ((selectedView === 'stiffness' || selectedView === 'eccentricity') && !stability) throw new Error('Rijitlik ve dışmerkezlik hesabı bulunamadı.');
      if (selectedView === 'cages' && !cages) throw new Error('Donatı önerisi bulunamadı.');
      if (selectedView === 'pmm' && !pmm) throw new Error('Koşullu PMM hesabı bulunamadı.');
      if (selectedView === 'transverse' && !transverse) throw new Error('Enine donatı önerisi bulunamadı.');
      if (selectedView === 'shear' && !shear) throw new Error('Koşullu kesme hesabı bulunamadı.');
      if (['joints','joint-ties'].includes(selectedView) && !joints) throw new Error('Birleşim referansları bulunamadı.');
      if (['end-forces','kinematics'].includes(selectedView) && !kinematics) throw new Error('Kolon uç kaynak bağı bulunamadı.');
      if (!page || (selectedView !== 'native' && page.view !== selectedView)) throw new Error('İstenen talep görünümü bulunamadı.');
      total = page.total; offset = page.offset;
      const identity = [['Obj','Kolon'], ['Elm','Analiz elemanı'], ['ObjSta','Nesne istasyonu'], ['ElmSta','Eleman istasyonu'],
        ['LoadCase','Vaka / birleşim'], ['StepType','Adım'], ['StepNum','No']];
      if (selectedView === 'native') {
        el('columnUnits').textContent = 'Native işaretler korunur. Kuvvetler kN, momentler kN·m, istasyonlar m.';
        el('columnForces').append(table([...identity,...['P','V2','V3','T','M2','M3'].map(c => [c,c])], page.rows));
      } else if (selectedView === 'static' || selectedView === 'critical') {
        el('columnUnits').textContent = 'N basınç pozitif = −P; çekme negatif kalır. Kuvvetler kN, momentler kN·cm, istasyonlar m; CSI yerel 2–3 eksenleri. Analiz mertebesi doğrulanmadı.';
        const reason = selectedView === 'critical' ? [['criticalReason','Kritik ölçüt']] : [];
        if (selectedView === 'critical') {
          if (!report.critical_scope || report.critical_scope.pmm_population_reduced !== false) throw new Error('Kritik seçim kapsamı doğrulanamadı.');
          el('columnContext').append(text('p', `${report.critical_scope.candidate_count} filtrelenmiş statik aday içinden kritik kayıtlar. ` +
            'Eşit kritiklerin tamamı korunur. Bileşen maksimumları tek vektöre birleştirilmez; PMM için tam aday nüfusu saklanır.', 'micro'));
        }
        el('columnForces').append(table([...reason,...identity,['N_compression_kN','N (basınç +)'], ['V2_kN','V2'],
          ['V3_kN','V3'],['T_kNcm','T'],['M2_kNcm','M2'],['M3_kNcm','M3']],
          page.rows.map(r => ({...r.native_key,...r.domain_values,criticalReason:(r.criteria || []).map(c => labels[c] || c).join(', ')}))));
      } else if (selectedView === 'reinforcement') {
        el('columnUnits').textContent = 'TBDY 2018 7.3.2.1 alan hesabı: As,min = %1 Ac; As,max = %4 Ac. Alanlar cm². Birleşimden bağımsızdır; süneklik sınıfı, gerçek donatı, çap/adet ve bindirme uygunluğu bu hesapla doğrulanmaz.';
        el('columnForces').append(table([['member_id','Kolon'],['story','Kat'],['section_name','Kesit'],
          ['gross_area_cm2','Ac'],['minimum_as_cm2','As,min'],['maximum_as_cm2','As,max'],['provided_as_cm2','Doğrulanmış mevcut As'],
          ['sourceMatches','Kaynak AsMin eşleşen'],['sourceAbove','Referans üstünde'],['sourceBelow','Referans altında'],
          ['sourceUnknown','AsMin belirsiz'],['label','Hesap'],['reason','Açık neden']], page.rows.map(r => ({...r,label:labels[r.status] || r.status,
            sourceMatches:r.asmin_source_counts.NUMERICAL_MATCH || 0,sourceAbove:r.asmin_source_counts.SOURCE_ABOVE_REFERENCE || 0,
            sourceBelow:r.asmin_source_counts.SOURCE_BELOW_REFERENCE || 0,
            sourceUnknown:Object.keys(r.asmin_source_counts).length ? (r.asmin_source_counts.NOT_PROVEN || 0) : 'Kayıt yok'}))));
      } else if (selectedView === 'stiffness') {
        const fmt = v => v == null ? null : Number(v.toPrecision(10));
        el('columnUnits').textContent = 'Brüt kesit: I cm⁴, r mm, E MPa; boylar m. E×I etkili rijitlik değildir. Çıktı aralığı TS500 serbest boyu veya etkili boy sayılmaz.';
        el('columnContext').append(text('p', `${stability.calculated_section_count} kolon · ${stability.distinct_section_count} farklı kesit · ` +
          `${stability.native_property_match_count} kaynak özellik eşleşmesi. ` +
          'İkinci mertebe için serbest boy, k, ötelenebilirlik, sünme ve analiz esası bekleniyor. r=√(I/A) ve 0,30h yaklaşımı ayrı değerlerdir.', 'micro'));
        el('columnForces').append(table([['member_id','Kolon'],['story','Kat'],['section_name','Kesit'],
          ['i22','I22'],['i33','I33'],['r22','r22'],['r33','r33'],['e','E'],['object','I–J boyu'],
          ['span','Çıktı aralığı'],['comparison','Kesit kaynak kıyası']], page.rows.map(r=>({...r,
            i22:fmt(r.section ? r.section.i22_mm4/1e4 : null),i33:fmt(r.section ? r.section.i33_mm4/1e4 : null),
            r22:fmt(r.section?.r22_exact_mm),r33:fmt(r.section?.r33_exact_mm),e:fmt(r.elastic?.observed_E_MPa),
            object:r.lengths.object_i_j_m,span:r.lengths.output_face_span_m,comparison:labels[r.property_comparison_status] || r.property_comparison_status}))));
      } else if (selectedView === 'eccentricity') {
        el('columnUnits').textContent = 'TS500 6.16: e,min = 15 + 0,03h (mm); N·e,min referansı kN·cm. Uç momenti hükmü için kaynak kıyasıdır; iç istasyonlara yönetmelik PASS/FAIL verilmez. Kuvvetler değiştirilmez.';
        el('columnContext').append(text('p', 'Native T3 yerel 2, T2 yerel 3 boyutudur. M2 için h=T2, M3 için h=T3. Basınç olmayan kayıtlarda bu referans uygulanmaz. Tasarım uçlarının ve birleşimlerinin kabulü ayrıca gereklidir.', 'micro'));
        el('columnForces').append(table([['Obj','Kolon'],['Elm','Analiz elemanı'],['ObjSta','İstasyon (m)'],['LoadCase','Birleşim'],
          ['n','N (kN)'],['m2','|M2|'],['ref2','M2 referansı'],['s2','M2 kıyası'],['m3','|M3|'],['ref3','M3 referansı'],['s3','M3 kıyası']],
          page.rows.map(r=>({...r.native_key,n:r.axes[0].n_compression_kn,m2:r.axes[0].source_abs_moment_kNcm,
            ref2:r.axes[0].reference_minimum_moment_kNcm,s2:labels[r.axes[0].status] || r.axes[0].status,
            m3:r.axes[1].source_abs_moment_kNcm,ref3:r.axes[1].reference_minimum_moment_kNcm,
            s3:labels[r.axes[1].status] || r.axes[1].status}))));
      } else if (selectedView === 'cages') {
        el('columnUnits').textContent = 'Üç öneri: 16Φ24 / 16Φ28 / 16Φ32; önerilen etriye Φ12. Model örtüsü etriyenin dış yüzünedir. Bunlar mevcut veya seçilmiş donatı değildir.';
        el('columnContext').append(text('p','Agrega, etriye/çiroz, bindirme ve malzeme katsayılarının proje kabulü açık. Kesitler boyuna yerleşim önerisidir; detay çizimi değildir. Yerel 2 sağa, yerel 3 yukarı.', 'micro'));
        if (member.value) for (const row of page.rows.filter(r=>r.geometry_status==='PROPOSED_GEOMETRY_CALCULATED')) {
          el('columnContext').append(cageDrawing(row));
        }
        el('columnForces').append(table([['member_id','Kolon'],['story','Kat'],['label','Öneri'],['as','As (cm²)'],
          ['rho','ρ (%)'],['center_offset_mm','Merkez örtüsü (mm)'],['minimum_clear_spacing_mm','Net aralık (mm)'],
          ['area','Alan kıyası'],['geometry','Geometri'],['reason','Açık neden']],page.rows.map(r=>({...r,
            as:rounded(r.as_cm2),rho:rounded(r.rho_percent),area:labels[r.area_ratio_status] || r.area_ratio_status,
            geometry:labels[r.geometry_status] || r.geometry_status}))));
      } else if (selectedView === 'pmm') {
        el('columnUnits').textContent = 'Değiştirilmemiş statik kaynak vektörü × öneri kafesi. M2/M3 ve radyal kapasite kN·m; oran boyutsuzdur. γc=1,5 / γs=1,15 senaryosu; minimum dışmerkezlik ve ikinci mertebe uygulanmadı.';
        el('columnContext').append(text('p',`${pmm.static_state_count} statik durum × 3 öneri = ${pmm.assessment_count} kıyas (arşivin tamamı). `+
          'Oran yalnız sayısal olarak çözülen senaryo içindir. Depremli tam tasarım nüfusu ve nihai donatı seçimi henüz doğrulanmadı.', 'micro'));
        el('columnForces').append(table([['Obj','Kolon'],['ObjSta','İstasyon (m)'],['Elm','Eleman'],['LoadCase','Birleşim'],
          ['candidate_label','Öneri'],['n','N (kN)'],['m2','M2'],['m3','M3'],['capacity','Radyal kapasite'],
          ['ratio','Koşullu oran'],['label','Sayısal durum'],['reasonLabel','Açık neden']],page.rows.map(r=>({...r.native_key,...r,
            n:rounded(r.domain_values.N_compression_kN),m2:rounded(r.native_values.M2),m3:rounded(r.native_values.M3),
            capacity:rounded(r.radial_capacity_kNm),ratio:rounded(r.utilization),label:labels[r.status] || r.status,
            reasonLabel:labels[r.reason] || r.reason}))));
      } else if (selectedView === 'transverse') {
        el('columnUnits').textContent = 'Φ12/100 önerisi: bir dış etriye + her yönde üç çiroz. Ash ve Asw mm², ölçüler mm. Ack dıştan dışa, bk etriye eksenleri arasındadır. Yüksek süneklik referansı; proje kabulü açık.';
        el('columnContext').append(text('p','İki eksenel yük dalının sargı alanları ayrı gösterilir; statik kuvvetlerden bir dal seçilmez. Serbest boy, gerçek sarılma bölgesi, kanca/kenetlenme ve üç boyutlu yerleşim henüz doğrulanmadı.','micro'));
        const drawn = new Set();
        if (member.value) for (const row of page.rows) {
          const cage = cages?.candidates?.find(c=>c.candidate_id===row.candidate_id);
          if (cage && row.layout && !drawn.has(row.candidate_id)) {
            el('columnContext').append(cageDrawing(cage,row.layout)); drawn.add(row.candidate_id);
          }
        }
        el('columnForces').append(table([['member_id','Kolon'],['candidate_label','Boyuna öneri'],['shear_axis','Kesme yönü'],
          ['bkAxis','bk ekseni'],['bk','bk'],['ash','Öneri Ash'],['reqHigh','Ash · yüksek N'],['reqLow','Ash · düşük N'],
          ['gap','Yatay kol aralığı'],['smax','Sarılma s üst sınırı'],['label','Hesap'],['reason','Açık neden']],page.rows.map(r=>({...r,
            bkAxis:r.direction?.bk_axis,bk:rounded(r.direction?.bk_mm),ash:rounded(r.direction?.ash_mm2),
            reqHigh:rounded(r.direction?.confinement.high_axial_required_ash_mm2),
            reqLow:rounded(r.direction?.confinement.low_axial_required_ash_mm2),gap:rounded(r.direction?.maximum_lateral_leg_spacing_mm),
            smax:rounded(r.confinement_spacing_max_mm),label:labels[r.status] || r.status}))));
      } else if (selectedView === 'shear') {
        el('columnUnits').textContent = 'Kuvvetler kN. V2: bw=T2, d=T3−merkez örtüsü; V3: bw=T3, d=T2−merkez örtüsü. Vr=Vc+Vw; oran |kaynak V|/Vr. Bunlar statik kaynak kıyaslarıdır; gerçek tasarım Ve doğrulanmadı.';
        el('columnContext').append(text('p',`${shear.static_state_count} statik durum × 3 öneri × 2 yön = ${shear.assessment_count} kıyas (arşivin tamamı). `+
          'Vc=0 deprem koşulu seçilmedi; iki senaryo birlikte gösterilir. Burulma etkileşimi, kapasite kesmesi ve nihai donatı seçimi açık.','micro'));
        el('columnForces').append(table([['Obj','Kolon'],['ObjSta','İstasyon (m)'],['LoadCase','Birleşim'],
          ['candidate_label','Boyuna öneri'],['shear_axis','Yön'],['v','İşaretli V'],['vc','Vc · TS500'],['vw','Vw'],
          ['vr','Vr · TS500'],['ratio','|V|/Vr · TS500'],['ratioZero','|V|/Vr · Vc=0'],['label','Hesap'],['reasonLabel','Açık neden']],
          page.rows.map(r=>({...r.native_key,...r,v:rounded(r.calculation?.source_signed_v_kn),
            vc:rounded(r.calculation?.branches.ts500.vc_kn),vw:rounded(r.calculation?.branches.zero_concrete.vw_kn),
            vr:rounded(r.calculation?.branches.ts500.vr_kn),ratio:rounded(r.calculation?.branches.ts500.source_utilization),
            ratioZero:rounded(r.calculation?.branches.zero_concrete.source_utilization),label:labels[r.status] || r.status,
            reasonLabel:labels[r.reason] || r.reason}))));
      } else if (selectedView === 'end-forces' || selectedView === 'kinematics') {
        el('columnContext').append(text('p',`${kinematics.linked_member_case_count}/${kinematics.expected_member_case_count} kolon–birleşim kaynak bağı. `+
          'Analiz mertebesi doğrulanmadı; Cm, β ve büyütülmüş moment üretilmez.','micro'));
        const details = text('details',''); details.append(text('summary','Analiz rijitliği kaynağı'));
        const names = kinematics.analysis_basis.combinations.find(c=>c.combination===loadCase.value)?.case_names;
        details.append(table([['case_name','Vaka'],['stiffness_type','Rijitlik ayarı'],['nonlinear_case_raw','Başlangıç vaka kaydı'],
          ['label','Kaynak durumu'],['reason','Açık neden']],kinematics.analysis_basis.cases.filter(c=>!names || names.includes(c.case_name))
          .map(c=>({...c,label:labels[c.status] || c.status}))));
        details.append(text('p','Lineer statik vaka türü birinci mertebe kanıtı değildir; kayıttaki “None” değeri doğrulanmış başlangıç koşulu sayılmaz.','micro'));
        el('columnContext').append(details);
        if (selectedView === 'end-forces') {
          el('columnUnits').textContent = 'Her satır aynı tek değerli statik birleşimde iki kaynak kesitini eşler. P çekme pozitif; kuvvetler kN, momentler kN·m, istasyonlar m. Çıktı kesitleri düğüm veya fiziksel destek yüzü kabul edilmez; ara istasyonlar korunur.';
          const values = (pair,end,keys) => pair?.[end] ? keys.map(k=>rounded(pair[end].native_values[k])) : null;
          el('columnForces').append(table([['member_id','Kolon'],['output_case','Birleşim'],['iCut','I: eleman / istasyon'],
            ['jCut','J: eleman / istasyon'],['iF','I: P / V2 / V3'],['iM','I: T / M2 / M3'],
            ['jF','J: P / V2 / V3'],['jM','J: T / M2 / M3'],['label','Kaynak bağı'],['reason','Açık neden']],page.rows.map(r=>({...r,
              iCut:r.force_pair ? [r.force_pair.i.native_key.Elm,r.force_pair.i.native_key.ObjSta] : null,
              jCut:r.force_pair ? [r.force_pair.j.native_key.Elm,r.force_pair.j.native_key.ObjSta] : null,
              iF:values(r.force_pair,'i',['P','V2','V3']),iM:values(r.force_pair,'i',['T','M2','M3']),
              jF:values(r.force_pair,'j',['P','V2','V3']),jM:values(r.force_pair,'j',['T','M2','M3']),
              label:labels[r.status] || r.status,reason:r.force_reason || r.kinematics_reason}))));
        } else {
          el('columnUnits').textContent = 'Global düğüm U/R değerleri kolonun yerel 1–2–3 eksenlerine dönüştürülür. Δu: mm, L: düğümler arası m; α2=−Δu3/L, α3=Δu2/L ve R−α: rad. Bunlar yuvarlanmış düğüm kinematiğidir; kesit eğriliği, P–δ veya kat stabilitesi sonucu değildir.';
          el('columnForces').append(table([['member_id','Kolon'],['output_case','Birleşim'],['points','I / J düğümü'],
            ['length','L (m)'],['delta','Δu1 / Δu2 / Δu3 (mm)'],['alpha','α2 / α3 (rad)'],
            ['ri','I: R2−α2 / R3−α3'],['rj','J: R2−α2 / R3−α3'],['label','Kaynak bağı'],['reason','Açık neden']],page.rows.map(r=>{
              const c=r.calculation; return {...r,points:[r.point_i,r.point_j],length:c?.object_i_j_length_m,
                delta:c?.delta_local_m.map(v=>rounded(v*1000)),alpha:c ? [rounded(c.chord_alpha2_rad),rounded(c.chord_alpha3_rad)] : null,
                ri:c ? [rounded(c.joint_i_relative_r2_rad),rounded(c.joint_i_relative_r3_rad)] : null,
                rj:c ? [rounded(c.joint_j_relative_r2_rad),rounded(c.joint_j_relative_r3_rad)] : null,
                label:labels[r.status] || r.status,reason:r.kinematics_reason || r.force_reason};})));
          el('columnContext').append(text('p','Tabloda sıfır yazması gerçek hareketin sıfır olduğunu kanıtlamaz. Düğüm dönmeleri, releases/offsets bulunan kolonun kesit uç dönmeleri yerine kullanılamaz.','micro'));
        }
      } else if (selectedView === 'joints') {
        el('columnUnits').textContent = 'TBDY 7.5 · Eşmerkez, dik kesit senaryosu. Dört yüzde kiriş ve her genişlik ≥ %75 koşuluyla sınıflandırılır. Kesme sınırları kN; Ve ve SCWB doğrulanmadı.';
        el('columnContext').append(text('p',`${joints.joint_node_count} düğüm · ${joints.column_end_count} kolon ucu · ${joints.geometric_limit_count} yön sınırı. `+
          'Her satırın kesiti o uç kolonuna aittir; birleşimin fiziksel yüzleri ve eksantrisitesi henüz bağlı değil.','micro'));
        if (joints.graph.reason) el('columnContext').append(text('p',joints.graph.reason,'warn'));
        el('columnForces').append(table([['member_id','Kolon'],['end','Uç'],['point_id','Düğüm'],['label','Eşmerkez sınıf'],
          ['v2','V2 sınırı'],['v3','V3 sınırı'],['missing_faces','Kirişsiz yüz'],['narrow_faces','Dar kiriş yüzü'],['reasonLabel','Açık neden']],
          page.rows.map(r=>({...r,label:labels[r.enclosure_scenario || r.status] || r.status,
            v2:rounded(r.axes.find(a=>a.axis==='V2')?.calculation?.geometric_limit_kn),
            v3:rounded(r.axes.find(a=>a.axis==='V3')?.calculation?.geometric_limit_kn),reasonLabel:labels[r.reason] || r.reason}))));
        if (member.value) for (const row of page.rows) {
          const details = text('details',''); details.append(text('summary',`${row.end} ucu · kiriş genişlikleri ve kaynak bağlantıları`));
          details.append(table([['face','Kolon yüzü'],['frame_id','Kiriş'],['native_end','Kiriş ucu'],['beam_section_name','Kesit'],
            ['beam_width_mm','Kiriş eni (mm)'],['column_transverse_width_mm','Kolon eni (mm)']],Object.values(row.faces).filter(Boolean)));
          el('columnContext').append(details);
        }
      } else if (selectedView === 'joint-ties') {
        el('columnUnits').textContent = 'TBDY 7.5.2.3 · Alt kolonun Denk. 7.1 sargı referansından %40/%60 × Ash/s aktarımı. Alanlar mm², aralık mm. İki N dalı açık kalır; kapasite kesmesi kaynaklı tam donatı ihtiyacı doğrulanmadı.';
        el('columnContext').append(text('p','Öneri aynı Φ12/100 yerleşimidir. Üst ve alt kolonun eksenleri fiziksel doğrultuyla eşlenir. Kuşatılmış/kuşatılmamış senaryoda aralık sınırı 150/100 mm, çap alt sınırı 8 mm; gerçek birleşim detayı henüz doğrulanmadı.','micro'));
        el('columnForces').append(table([['member_id','Uç kolonu'],['end','Uç'],['point_id','Düğüm'],['lower_column_id','Alt kolon'],
          ['axis','Uç yönü'],['lower_axis','Alt kolon yönü'],['candidate_label','Boyuna öneri'],['high','Ash · yüksek N'],
          ['low','Ash · düşük N'],['ash','Öneri Ash'],['s','Öneri s'],['reasonLabel','Açık neden']],page.rows.map(r=>({...r,
            high:rounded(r.branches.high?.required_ash_at_joint_spacing_mm2),low:rounded(r.branches.low?.required_ash_at_joint_spacing_mm2),
            ash:rounded(r.branches.high?.proposed_ash_mm2),s:r.branches.high?.joint_spacing_mm,
            reasonLabel:labels[r.tie_reason] || r.tie_reason}))));
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
      el('columnPage').textContent = total ? `${offset + 1}–${Math.min(offset + page.limit,total)} / ${total}` : 'Bu filtre ve görünüm için gösterilecek kayıt yok.';
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
