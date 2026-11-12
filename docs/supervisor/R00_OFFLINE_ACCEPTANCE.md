# R00 — Kanonik VS27 paketleri, Codespaces ve offline kaynak kabulü

**12 Kasım 2026 · feridunfc/YENI · Supervisor scope: R00 + offline R01 triage**

## 1. Kaynak / yetki

- Değiştirilemeyecek başlangıç: `work/vs07-b2-soft-story-20261108` @ `14ddf197ca8279ea34107eac0344acbabc7327aa` (VS26).
- Bu çalışma dalı: `recovery/r00-r01-vs27-source-20261112`.
- `main`, PR #6 ve eski ZIP/SQLite kanıtları değiştirilmez; commit/push yalnız recovery dalında. **MERGE HOLD.**
- VS27 tam test paketi ve VS27.1→VS27.2→VS27.3 düzeltmelerinin SHA-256'ları `config/r00_vs27_artifacts.json` ile sabittir.
- Bu repoya kullanıcı ETABS modeli, ham ZIP, büyük SQLite veya kişisel kaynak verisi eklenmez. Yalnız kod, manifest ve kaynaktan türetilmiş toplamlar.

## 2. İşlem sırası — Github Codespaces / Linux

Gerçek Windows ETABS'a bağlanma, COM çağırma, yeni analiz, model kaydetme, tasarım başlatma ve görüntülenen seçimleri değiştirme **yok**.

1. Codespaces terminalinde yeni recovery dalını checkout et; `git status --porcelain` ile çalışma ağacının temiz olduğunu doğrula.
2. Önce `python -m unittest discover -s tests -p 'test_r00_*.py' -v` çalıştır.
3. 11–12 Kasım ZIP'lerini Git deposunun **dışında**, ör. `/tmp/yeni-r00-input/` veya `.private_sources/` içinde tut. `git add` ile bunları depoya ekleme.
4. Offline kaynak kapısını çalıştır:

```bash
python tools/r00_offline_gate.py \
  --archive /tmp/yeni-r00-input/YENI_ALL_COLUMNS_20261112T0424500139481Z.zip \
  --expected-columns 87 \
  --require-force \
  --output /tmp/r00_source_gate.json
```

**Tarihsel 12 Kasım arşivinin beklenen sonucu:** JSON üretir, fakat `exit=2`, `source_readiness=BLOCKED_NO_NATIVE_FORCE_ROWS`, `member_count=87`, `native_force_rows=0`. Bu bir test başarısızlığı değil, doğru fail-closed mühendislik sonucudur. İsteğe bağlı SQLite (`--database /path/to/immutable.sqlite`) sadece `mode=ro` açılır ve `PRAGMA quick_check`/SHA denetlenir.

5. `python tools/r00_stage_vs27.py --inputs /tmp/yeni-r00-input --out /tmp/yeni-vs27-staged` komutuyla kaynak ZIP ve düzeltmeleri **ayrı bir staging klasörüne** çıkar. Script kaynak SHA, ZIP FILE_MANIFEST ve her düzeltme eski/yeni hash koşulunu doğrulamalı; doğrulanmamış paketi geçirmemeli. Çalışma ağacının üzerine kör kopyalama yok.
6. Staged dosyaları `git diff --no-index` ile VS26 dalına karşı incele; bağımsız rapor ve QA kabulü sonrasında kod entegrasyon PR'ı hazırlansın.

## 3. R00 çıkış kapısı

| Gate | Kabul ölçütü | Durum |
|---|---|---|
| Git baseline | Repo ve kaynak SHA sabit; yeni dal mevcut | VERIFIED |
| Offline package SHA | VS27 + üç düzeltme paketinin hash'leri biliniyor | PINNED |
| Historical archive integrity | 87 kolon ZIP manifesti / içerik hash'leri geçerli | VERIFIED |
| Native force payload | 87/87 `FrameForce` satırı ve gerekli vaka/istasyonlar | BLOCKED (0/87) |
| Static/spectral replay | Tam kaynak üzerinde bağımsız karşılaştırma | NOT_RUN / BLOCKED |
| Golden / normatif / release | Uygulanabilirlik, as-built analiz, bağımsız hesap | NOT_PROVEN / NOT_READY |

## 4. R01'e geçiş

Canlı ETABS kullanılamayacağı için yeni sonuç üretmeye çalışılmaz. Offline bir arşivde yeterli **mevcut** native kuvvet dizileri varsa, tasarım talebi ancak aynı nesne/analiz nesli, istasyon, yük vakası, StepType/StepNum ve birim bağları doğrulandıktan sonra replay edilir. **Kaynak tablo var** ifadesi, **tasarım hesabı kabul edildi** anlamına gelmez.

Bu sprintin başarılı sonucu: kontrol edilebilir tek kaynak, tekrar çalıştırılabilir offline gate ve somut blokaj; **87 kolonun tasarımının tamamlanması değildir**.
