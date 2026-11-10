# VS10 — Deprem birleşim katsayıları ve iki yönün kaynak kapsamı

Kullanıcı VS09'un 500 testini başarılı bildirdi. Aynı worker dalında iki hazır
kaynak kontrolü **Analiz vakaları** menüsüne, ortak JSON ve yazdırılabilir HTML
raporuna bağlandı. Katalog 16 tekil kayıt; tek gateway ve eski receipt'ler korunur.

| Kontrol | Kaynak → hesap | Sınır |
|---|---|---|
| `earthquake_100_30` | Seçili gerçek RS X/Y kimlikleri + native kombinasyon grafiği → min(\|aX\|,\|aY\|) / max(\|aX\|,\|aY\|) = 0.30 | Denk.(4.9) katsayı alt koşulu; tek yön/diğer yönde sıfır koşulu sağlamaz. |
| `earthquake_direction_pairs` | Aynı diğer **işaretli** vaka katsayıları ve aynı pozitif ortak yatay çarpan → X ve Y baskın birleşimler | Gözlenen tanımlarda iki yönün kapsamı; işaret zarfı veya tasarım kabulü değildir. |

Kabul edilmiş D4 operatör/referans çözücüsü isteğe bağlı typed graph döndürür;
mevcut çağrıların özet ve hash çıktısı değişmez. Katsayılar `Fraction` ile tam
rasyonel aritmetik kullanır; kararlar yuvarlatılmış ekran değerine dayanmaz.
Yalnız Linear Add zincirleri açılır. Envelope seçenekleri ayrı tutulur, toplanmaz.
Tekrarlı referanslar bu sınırlı adaptörde desteklenmez; ETABS model hatası sayılmaz.
Bozuk kimlik, birim, satır veya bağlam; döngü, bilinmeyen referans ve desteklenmeyen
işlem kayıp satır yaratmadan görünür `NOT_PROVEN` üretir. Birleşim adları rol veya
eşleştirme belirlemez. Kontroller aynı arşivden türetilir; ek COM okuması yapılmaz.

Gerçek arşivde 271 kaynak satırı, 35 birleşim: 30 Linear Add ve 5 Envelope.
Seçili RS çiftini içeren **24/24** doğrusal birleşimde oran tam 3/10'dur:
16'sında 1/0.3, 8'inde 2.5/0.75. Diğer işaretli yük katsayıları ve ortak çarpana
göre **8/8** bağlamda iki baskın yön vardır. 6 doğrusal birleşim yalnız seçili
RS çiftinin kapsamı dışındadır; deprem dışı oldukları çıkarılmaz. 5 zarf ayrı
gösterilir. Ham kaynak, özel model ve model çıktıları depoya eklenmez.

Doğrulama: 522/522 Python testi; UI kayıt değişimi/geç yanıt, sekme yönlendirmesi
ve JavaScript sözdizimi başarılı. 22 yeni test kaynak, kesin aritmetik, kapsam,
HTTP/JSON/HTML ve receipt değişmezliğini kapsar. Bağımsız incelemede modal vaka
tür kapısı sıkılaştırıldı; gerçek arşiv sonuçları bağımsız Fraction hesabıyla eşleşti.

± işaretlerin bütünlüğü, tasarımda kullanılan birleşimler, ortak çarpanın D
olduğu, 4.10 iç kuvvet kuralları, düşey deprem/diğer yük kuralları, eşzamanlı
kuvvet vektörleri ve analiz nesli kanıtlanmış değildir. `NOT_PROVEN / NOT_READY`
korunur. Windows/ETABS ve toplu kullanıcı kabulü sonda; `main` merge bekler.

Birincil dayanaklar: [TBDY 2018, 4.4.2.1 / Denk.(4.9), Resmî Gazete nüshası](https://izmir.imo.org.tr/Eklenti/89%2Cdepremyonetmeligipdf.pdf?0=);
[CSI ETABS — Load Combination Data](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Combinations/Load_Combination_Data_Form.htm)
(Linear Add, Envelope ve tekrarlı terim davranışı).
