# VS07 — B2 koşullu kaynak hesabı

Başlangıç: main 49f25f9a274c3a62d988f853a9e714ec4a7e6ca0.
Tek yeni kontrol: SOFT_STORY_B2. Mevcut gateway, DAG ve run_id korunur.

## Hesap ve otorite sınırı

TBDY 2018 Tablo 3.6, §3.6.2.1 için aday hesap:
ηki = (AvgDriftᵢ / hᵢ) / (AvgDriftⱼ / hⱼ).
Her katın üst ve alt komşusu X/Y için ayrı hesaplanır; eşik kesin olarak
> 2,0'dır. Tam 2,0 bu sayısal eşiği aşmaz.
Yönetmelik bodrum uygulanabilirliğinin belirlenmesini ve §4.7 kapsamında
±%5 ek dışmerkezliği dikkate alan ötelemeleri gerektirir.

Mevcut RSX/X ve RSY/Y Max satırları bu hesap esası için onaylı değildir.
ETABS Avg Drift alanının yönetmelikteki ortalamaya eşdeğerliği de kanıtlanmadı.
Bu alan yalnız açık bir ortalama öteleme varsayımıyla kullanılır:
CONDITIONAL_AVERAGE_DRIFT_SCENARIO; formal_compliance=NOT_PROVEN;
normative_b2_classification=NOT_PROVEN; engineering_release=NOT_READY.
Sonuç B2 VAR/YOK veya bina PASS kararı değildir.

## Mevcut kaynağın kullanımı

Mühürlü vs05_delta_source içindeki Story Definitions, Tower and Base Story
Definitions, Story Max Over Avg Drifts ve Story Drifts kullanılır.
Yeni COM çağrısı yoktur. Kaynak SHA, gerçek alanlar/birimler, satır sayısı ve
vaka/yön/Max kimliği doğrulanır. Aynı satırın Avg Drift, Max Drift ve Ratio
uyumu ile Story Drifts × h / Max Drift çapraz kontrolü yapılır.
Numaralı adım, yinelenmiş vaka/yön kaydı ve bilinmeyen şema reddedilir.
Bağımsız RS nokta maksimumları çıkarılmaz; bağımsız kat zarfları oluşturulmaz.

Kat sırası mevcut üstten alta ETABS tablo sırasından, BSElev ve yüksekliklerle
kurulan aday sıradır. Noktanın Story etiketi üst düzlemde olmasını gerektirmez:
Z, ilgili [üst kot − h, üst kot] aralığında 10⁻⁶ m toleransıyla denetlenir.
Yalnız üst düzlem noktaları kotu destekler; ara ve alt sınır noktaları ayrı
sayılır. Aralık dışı nokta ve ters kat sırası reddedilir. Kotlar/yükseklikler
noktalara uydurulmaz; destekleyici nokta yokluğu ayrıca açıkça gösterilir.
Kat adı kot olarak ayrıştırılmaz. Tüm tanımlı katlar korunur; eksik orta
kat atlanmaz, boş olduğu düşünülen üst kat otomatik dışlanmaz.
n kat için 2n kaynak yuvası ve 4(n−1) yönlü komşuluk ayrı sayılır.
Sıfır payda çözümsüzdür. İlgisiz tablo hatası B2'yi, B2 hatası önceki
kontrolleri kilitlemez. Eski kaynak ve receipt dosyaları değişmez.

## Bağımsız sayısal örnek ve kabul

Sentetik örnek: alt→üst h = 4, 3, 5 m; X ortalama adayları =
0,012; 0,003; 0,010 m. Normalize değerler 0,003; 0,001; 0,002;
yönlü oranlar 3, 1/3, 1/2, 2. Son oran tam sınırdadır.
Bu sentetik örnek gerçek ETABS kabul kanıtı değildir.
VS05 tarihsel 12-satırlık testte Avg=Max yer tutucusu kullanıldığı için o
dosya gerçek B2 ortalama kanıtı olarak kullanılmaz.

Mevcut kayıtla Windows kabulü (ETABS'ı yeniden çalıştırmadan):

    python -m tools.verify_vs07_b2_archived --root .receipts --latest --export-dir out/vs07_b2

Kesin kayıt seçimi için --latest yerine --run-id RUN-... kullanılır.
Düzensizlikler sekmesindeki B2 paneli aynı JSON sonucunu okur; tam JSON ve
HTML/PDF raporunda kaynak, iki komşu hesabı, eksikler ve varsayımlar bulunur.
Gerçek kullanıcı kaydında replay ve Windows regresyon kabulü ayrıca gerekir.

## Arayüz ve ilerleme sırası

Sol menü: Model/kaynaklar, Bina/deprem, Betonarme elemanlar, Temeller.
Malzeme kontrolü Malzeme'de; modal kütle Modal analiz'de; STORY_DRIFT ve
C2 senaryosu Kat/sistem sonuçları'nda; A1 X/Y, B1 ve B2 Düzensizlikler'de;
kiriş/kolon kontrolleri kendi eleman başlıklarındadır. Katalog 11 tekil
kontrol içerir: B1 ve STORY_DRIFT zaten mevcut hesapların menü bağlarıdır;
bu sprintte yeni hesap yalnız B2'dir. C2 ayrıca sayılmaz.
Sağ panel model, kaynak/vaka ve kısa çalışma kimliğini gösterir.
Aşama kayıtları orta panelde açılır; rapor düğmeleri tüm sekmelerde görünür.
Kayıt değişimi eski B1/B2/C2 sonuçlarını temizler; geç gelen yanıtlar seçili
kayıtla karışmaz. B1 dosya hesabının R/dolgu seçimi kendi panelindedir.

Sonraki kontrol seçimi, mevcut kaynak ve bağımsız doğrulama olanağına göre
kolaydan zora yapılır: doğrudan alan/birim karşılaştırmaları → katlar arası
türetilmiş hesaplar → analiz esası/dışmerkezlik gerektiren kontroller →
donatı, kapasite ve birleşim kontrolleri. Yeni kaynak olmadan bu aşamalar
tamamlanmış sayılmaz; 68 kontrol için yapay hazır olma yüzdesi üretilmez.

## Birincil kaynaklar

- [AFAD, TBDY 2018, Tablo 3.6, basılı s.20](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf).
- [Bakanlık, TBDY 2018, §3.6.2.1](https://webdosya.csb.gov.tr/db/yapiisleri/icerikler/tbdy_2018-20210506174126.pdf).
- [CSI RSA açıklaması](https://web.wiki.csiamerica.com/wiki/spaces/etabs/pages/1474589/Torsional%2BIrregularities%2Bcheck%2Bfor%2BResponse%2BSpectrum%2BAnalysis%2BRSA):
  ayrı tepki büyüklüklerinin maksimumları eşzamanlı işaretli değerler değildir.
  Bu kaynaktaki ASCE yordamı TBDY B2 hesabına aktarılmamıştır.
