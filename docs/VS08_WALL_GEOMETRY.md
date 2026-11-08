# VS08 — Perde geometrisi kaynak alt kontrolleri

Tek yeni katalog/DAG kimliği: `WALL_GEOMETRY_CHECK`; sol menü **Perdeler**.
Katalog toplamı 12; eski değerlendirme kayıtları ve receipt'ler değişmez.
Mevcut B1 geometri ve VS05 kat kaynakları kullanılır; yeni gateway/COM okuması yoktur.

## Hesap kapsamı

TBDY 2018 7.6.1.2 ve standart (a) dalı için üç koşullu sayısal karşılaştırma:

| Girdi | Karşılaştırma |
|---|---|
| Kaynak panel uzunluğu / gerçek kalınlık | `l_panel / bw >= 6` |
| Gerçek kalınlık | `bw >= 250 mm` |
| Kaynak kat yüksekliği | `bw >= h_story / 16` |

ETABS alan panelinin bütün fiziksel perde/kol olduğu onaylanmaz. Bir panelin
oranının 6'dan küçük olması tek başına perdenin yönetmeliğe aykırı olduğunu
göstermez. Genel kalınlık dalı da bodrum veya diğer istisnaları yetkilendirmez.
7.6.1.2(b) tutulmamış plan boyu kaynaktan kanıtlanmadığı için hesaplanmaz;
panel uzunluğu bu değerin yerine kullanılmaz. İki uç mesnetlenmesi (c),
7.6.1.3/Denk.(7.14), yüksek bina 13.1.6 ve 7.6.1.1 eksenel kuvvet/net alan
koşulları ayrı `NOT_PROVEN` olarak kalır. Genel release `NOT_READY`.

## Kaynak ve geometri

Mühürlü geometri/kat kayıtlarının model, birim, nokta ve yükseklik izleri eşleşir.
Wall Object Connectivity ile Wall türündeki alan atamalarının **birleşimi**
beklenen nesne kümesidir; eksik bağlantı/atama paydadan silinmez. Kesit ve native
malzeme türü eşleştirilir; malzeme veya kesit adından beton/bodrum kararı çıkmaz.
Dört köşeli düşey dikdörtgen panel, dönük plan doğrultularında da çözülür.
Varsa native tam köşe listesiyle çelişki reddedilir. Panel kat bandı içinde
kalmalıdır; kısmi panel yüksekliği `h_story` yerine geçirilmez.
Tablodaki Area/Perimeter çapraz kontrolünde iki ondalık görüntü yuvarlaması için
en çok 0.005 birim payı kullanılır; daha hassas kaynak korunur, gerçek fark reddedilir.

## Bağımsız sınır örnekleri

| l (mm) | bw (mm) | h (mm) | l/bw | Genel bw,min (mm) | Genel dalın sayısal sonucu |
|---:|---:|---:|---:|---:|---|
| 1500 | 250 | 4000 | 6 | 250 | Üç eşitlik/sınır sağlanır |
| 7500 | 250 | 5000 | 30 | 312.5 | h/16 sağlanmaz; iki uç tutulması ayrıca kanıt ister |
| 1200 | 200 | 4000 | 6 | 250 | İki kalınlık koşulu sağlanmaz; 7.6.1.3 otomatik seçilmez |

Python testleri aritmetik, kaynak saldırı/eksiklikleri, JSON/HTML ve receipt
değişmezliğini; Node testi menü yerleşimi ve geç yanıtın başka kayıtla
karışmamasını denetler. Gerçek ETABS/Windows ve toplu kullanıcı kabulü ayrıdır.

Birincil kaynaklar: [AFAD TBDY 2018](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf)
ve [Bakanlık nüshası, PDF s.146](https://webdosya.csb.gov.tr/db/yapiisleri/icerikler/tbdy_2018-20210506174126.pdf#page=146).
7.6.1 basılı s.126; 13.1.6 basılı s.268.
