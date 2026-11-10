# VS09 — Hazır kaynaklardan iki mühendislik alt kontrolü

Kullanıcı VS08'in 480 testini başarılı bildirdi; benzer küçük kontrolleri paketlemeyi
istedi. Aynı worker dalında iki kontrol, **Malzeme** ve **Modal analiz** menülerine
bağlandı. Katalog 14 tekil kayıt. Tek gateway, kaynak ve eski receipt'ler korunur.

| Kontrol | Kaynak → hesap | Kapsam |
|---|---|---|
| `concrete_fck_80` | Mevcut native beton türü + Material Properties – Concrete Data.Fc; aynı kabul edilmiş birim dönüşümü → Fc ≤ 80 MPa | 7.1.3 / 7.2.5.3(a). 80 üstü `ABOVE_TBDY_STRENGTH_SCOPE`; sıradan dayanım yetersizliği değildir. Mevcut C25 alt kontrolü değişmez. |
| `modal_combination_spacing` | Modal kütle mod listesi + mühürlü periyot tablosu + seçilmiş spektrum modal satırları + vaka tanımı → kısa/uzun T < 0.8 | 4B.2.4(d). Eşitlik SRSS izni sağlamaz. `ModalCombo`, `DirCombo` ile karıştırılmaz. CQC seçimi kuvvet/korelasyon doğrulaması değildir. |

Pozitif periyotlar sıralanır. Bütün farklı çiftlerin oranı, sıralı komşu çiftler
arasındaki en büyük oranla sınırlıdır; N mod için N−1 karşılaştırma yeterlidir.
Bu sonuç bağımsız tüm çiftler/Fraction hesabıyla test edilir. Kaynaktan mod
çıkararak kapsam daraltılmaz; seçilmiş spektrum, modal kütle ve periyot mod
kimlikleri bire bir uyuşmalıdır. Kayıp/tekrarlı/başka modelden satırlar görünür
`NOT_PROVEN` üretir; kaynaklardan biri bozuksa diğer kontrol çalışmaya devam eder.

Bağımsız sınırlar: 79.999 ve 80 MPa üst sınırı sağlar; 80.001 aşar. T=(1,0.79,0.63)
s için tüm çift oranları 0.8'den küçüktür; 0.63 yerine 0.632 olduğunda eşitlik
oluşur ve SRSS ayrıklığı sağlanmaz. Bu koşula ek %5 sönüm kısıtı konulmaz.

Gerçek arşivde bir kullanılan beton malzemesi Fc=35 MPa; RSX/RSY için 100'er mod,
4950 farklı çift ve 99 komşu çift vardır. 95 komşu çift SRSS ayrıklığını sağlamaz;
her iki vakada da kaynak `ModalCombo=CQC`, `DirCombo=SRSS` bildirir. Bunlar
gösterilen kaynak değerlerinin sonuçlarıdır; yuvarlanmamış çözüm, analiz nesli,
TS EN 206 sınıfı/yaşı, deprem elemanı uygulanabilirliği, CQC sönüm/korelasyon ve
birleşmiş kuvvetler ayrıca doğrulanmış değildir. `NOT_PROVEN / NOT_READY` korunur.

7.4.1.1 kiriş/döşeme ve serbest açıklık girdileri bu arşivde eksiktir. 4.7.4,
Denk.(4.29) Di katsayısı eşdeğer deprem yükü yöntemine aittir; mevcut LinRespSpec
sonuçlarına ek büyütme olarak aktarılmamıştır. Bu iki konu yeni kontrol diye sayılmaz.

Birincil kaynak: [AFAD TBDY 2018](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf),
4B.2.4(d) basılı s.66–67, 7.1.3 s.111, 7.2.5.3(a) s.112;
[Bakanlık nüshası](https://webdosya.csb.gov.tr/db/yapiisleri/icerikler/tbdy_2018-20210506174126.pdf).
Windows/ETABS ve toplu kullanıcı kabulü sonda; `main` merge bekler.
