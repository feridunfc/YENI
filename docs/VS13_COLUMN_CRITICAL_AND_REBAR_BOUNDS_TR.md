# VS13 / CE-02B — kritik statik kayıtlar ve donatı alan sınırları

- Mevcut offline ZIP/SQLite üzerinden 87 kolonda 2.412 statik adaydan 634 kritik tam vektör işaretlendi; PMM için tüm adaylar korunur.
- Basınç, çekme, |M2|, |M3|, |V2|, |V3| ve |T| ölçütleri; her filtrede yeniden seçim, tüm eşit kritikler ve özgün satır kimlikleri korunur.
- Eşitlik native değerlerin Decimal karşılaştırmasıyla belirlenir; kayan noktalı birim dönüşümü farklı momentleri aynı kritik yapamaz. Ayrı satırların maksimumları birleştirilmez.
- [TBDY 2018 §7.3.2.1](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf) alan alt hesabı: Ac=b2×b3, As,min=0,01Ac, As,max=0,04Ac; 87 adet 80×80 cm kesitte 64–256 cm².
- 402 ham ETABS AsMin kaydı: 0,0064 m² × 10.000 = 64 cm²; tamamı alt sınırla sayısal eşleşti. Bu kayıtlar yerleştirilmiş donatı değildir.
- Süneklik uygulanabilirliği, gerçek kafes, çap/adet, bindirme, G+Q+E maksimum eksenel talebi ve kapasite kabulü açık: DENIED / NOT_PROVEN / NOT_READY; %6 bindirme sınırı genel %4 yerine kullanılmaz.
- Kolonlar → Görünüm: Kritik statik kayıtlar / Boyuna donatı alan sınırları; ikincisinde birleşim filtresi kapalı. Tam JSON ve HTML aynı hesabı taşır; CHECK sayısı 16 olarak korunur.
- Bağımsız gerçek veri kontrolü: 609 ölçüt kümesi, 634 tam vektör, 87 alan hesabı, 402 AsMin karşılaştırması. ZIP, SQLite ve önceki CE-02A sonuç hash'i değişmedi; yeni veri yazılmadı.
- 598 Python testi, iki Node arayüz regresyonu; 21 yeni test Windows CI kapsamına eklendi. Bu yazılım ve kaynak aritmetiği doğrulamasıdır.
- [Windows güncelleme ve mevcut arşivi açma komutları](VS12_CE02_COLUMN_DEMAND_CHAIN_TR.md#windows-zip-klasörü-yerine-git-çalışma-kopyası) geçerlidir; yeniden ZIP içe aktarımı gerekmez. Worker dalı ve PR #6 üzerinde devam; main birleşimi ortak kabulü bekler.
