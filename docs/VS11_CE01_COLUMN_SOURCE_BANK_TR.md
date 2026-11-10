# VS11 / CE-01 — kolon kaynak bankası

**Karar:** YENI ürün, ETABS gateway ve sonuç sahibi olarak kalır. İlk uyarlama
Column-Engine'in native kuvvet/context okuma yoludur. Kanonik hesap seçimi
değişmez: TBDY talep/ikinci mertebe/PMM/donatı çekirdekleri; Column bağımsız
sayısal kalite. Bu sürüm yalnız kuvvet bankası ve sınırlı statik yeniden hesaptır.

## Bu sürüm

- 87 seçili kolon, 159 analiz elemanı, 34.170 tam `P,V2,V3,T,M2,M3` satırı.
- 56 çıktı = 21 vaka + 35 birleşim; tanımlı beş vaka için kuvvet satırı yok.
- Eski “üç vaka” sınırı arşiv sınırı değildi; eski denetimin seçtiği kapsamdı.
- Altı statik Linear Add birleşimi: 2.412 satır / 14.472 skaler kıyas;
  bağımsız oracle ile aynı en büyük mutlak fark `5.8368e-13` native kN/kN-m.
- D7-B6'nın dokuz tarihsel imzalı P toplamı tekrar üretildi; kaynak DB değişmedi.
- 84 kolonda J çıktı istasyonu düğümden 0,70 m aşağıdadır. Obje, analiz
  elemanı, iki istasyon ve adım kimlikleri korunur; TS500 boyu türetilmez.
- Kolonlar sekmesinde ayrı arşiv seçimi, kuvvetler, eksikler ve JSON/SQLite/HTML.
- `NUMERICAL_MATCH` yalnız kaynak aritmetiğidir. Tasarım yetkisi `DENIED`,
  mühendislik kabulü `NOT_PROVEN / NOT_READY`; bina kolon nüfusu ayrıca kanıtlanmadı.

Doğrulama: **550/550 Python testi**, mevcut ve yeni Node arayüz regresyonları.
28 yeni test kaynak bozulması, eksik kolon/satır, analiz elemanı ve adım ayrımı,
yanlış kuvvet değeri, spektral/zarf kapsamı, salt okunur DB, API ve çıktı bağını sınar.
Bu testler Windows/ETABS ve normatif mühendislik kabulü yerine geçmez.

## Kaynak ve uyarlama sınırı

Column-Engine `4f0afbeb67fd3e7c7d140cd9eb4eda2f191631ca`:
`recipe_v11/bank.py`, `r6_source_bank.py`, `r6_member_context.py`,
`tools/audit_d7b13_native_frameforce.py`. Yeniden kullanılan imzalar YENI'nin
yerel ZIP/receipt sınırına uyarlandı; eski COM toplama veya uygulama katmanı kopyalanmadı.

TBDY `1440df1b9300f75b1e604204438f5cada9ebd247` talep sınıflandırması ve
Column `9269a00f5f5471ab68413c039912cafb2cf4db39` yakınsama yolu sonraki bağların
referansıdır. Spektral işaret permütasyonları bu sürümde tasarım yetkisi kazanmaz.

Tam parent ZIP SHA-256: `3882b659937626bb3bbfe841e6dbd6c57798fcfcce8e6fa54a683a221210fee3`.
B13 subset SHA-256: `e37079e2279ff9e1eb1e972d176d6e02293e4fbd126ef738d33c31b9ba77ae30`.
Tam parent'ta 4.142 manifest kaydı doğrulandı. B13 aynı kuvvet satırlarını sağlar,
ancak tam vaka/birleşim tanımları ve capture bağlamı olmadan statik replay açılmaz.
Gerçek ZIP, SQLite, JSON ve model yolları Git'e konulmaz.

## Çalıştırma

Proje kökünde, etkin sanal ortamla; ZIP/DB yollarını kendi dosyalarınıza göre yazın:

```powershell
python -m pip install -e .
python -m tbdy_next.cli import-column-bank --input "full-model-evidence(2).zip" --historical-db "D7B6_offline_evidence.sqlite" --out .receipts
python -m unittest discover -s tests -v
python -m tbdy_next.cli serve --host 127.0.0.1 --port 8765 --out .receipts
```

`--historical-db` isteğe bağlıdır. UI: **Kolonlar → Kuvvet bankası ve statik
birleşimler → Arşiv seçin**. Canlı ETABS hesabı bu arşivi otomatik seçmez veya birleştirmez.

**Sonraki bağlar:** tasarım birleşimi seçimi ve RS işaret/eşzamanlılık esası;
analiz nesli; k/EI ve P–Δ/P–δ; gerçek veya açıkça tasarlanmış donatı kafesi;
etriye/çiroz topolojisi ve tam birleşim/aynı kesit nüfusu. Yeni ETABS edinimi,
bu girdilerden arşivde bulunmadığı somut olarak belirlenenlere hedeflenmelidir.
