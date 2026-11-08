# VS06-D1 — B1 zayıf kat / gerçek `kompakt_b.EDB` kaynakları / dolgu varsayımı

**Dal:** `work/vs06-story-drift-coverage-20261108`. **PR:** #5, DRAFT, MERGE HOLD. Ana dal değişmeyecek. **Norm:** TBDY 2018 Tablo 3.6 ve §3.6.2.3.

## Gerçek ETABS giriş kaynakları

- `LC_WDL_OBJECT_20261108_160653.json`: Orijinal kaynak SHA256 `2fe66bff1247b4f8c59b89d68b739ef73d305ca00e72eb0507ccb8c87a83de8f`; 180/180 kiriş sorgusu; 72 kuvvet ataması, 70 farklı kiriş; iki adet yinelenen atama 996 ve 997 (ikisi de +0.00, Y yönünde), yüklerin fiziksel etkileşimi değil birleşik yerçekimi kuvveti toplanır, duvar uzunluğu bir kez sayılır.
- `B1_GEOMETRY_20261108_161525.json`: Orijinal kaynak SHA256 `f77ad99011abb546bada8cc0c1001dd883078b544ed01381ca198ba2593b15f1`; 8/8 kaynak tablo CAPTURED; 325 nokta, 87 kolon, 30 perde, 294 çerçeve kesit ataması, 4 kat tanımı.
- Her iki dosyada `C:\tmp\kompakt_b.EDB`, kN–m–C, kilitli model. **İki okumanın aynı ETABS analiz nesli olduğuna ilişkin bağımsız kanıt yoktur.** Sayısal sonuç senaryodur.

## 1. Yön ve kat eşleştirmesi

`FrameObj.UniqueName` -> `Beam Object Connectivity` -> `UniquePtI/UniquePtJ` -> `Point Object Connectivity X,Y` -> kiriş plan doğrultusu. Yatay ve dik yönü karıştırma. ETABS Story etiketi, ilgili kolon/perde diliminin üst kotu olarak yorumlanır.

| ETABS dilimi | X yüklenen kiriş / m | Y yüklenen kiriş / m | Brüt kat yüksekliği / m | Üst kiriş t3 / m | Net duvar yüksekliği / m |
|---|---:|---:|---:|---:|---:|
| +0.00 | 10 / 51.20 | 8 / 39.20 | 5.15 | 0.70 | 4.45 |
| +4.50 | 19 / 96.40 | 19 / 83.40 | 4.50 | 0.70 | 3.80 |
| +9.00 | 5 / 35.00 | 9 / 52.00 | 4.50 | 0.70 | 3.80 |
| Toplam | 34 / 182.60 | 36 / 174.60 | | | |

`+14.5` yalnız boş ETABS kat tanımı olarak korunur; mevcut fiziksel kolon/perde/kiriş odaklı envanterde aktif taşıyıcı dilimi bulunmadığından *koşullu sayısal* B1 çiftlerine katılmaz; tam Null/mesh/yapı envanteri sertifikası yerine geçmez.

## 2. Tuğla kesit alanı ile cephe alanı kesin ayrımı

ETABS yayılı yük satırı `q` [kN/m]. Üst kirişin gerçek atanmış betonarme kesitinden `t3` [m]. Her kiriş için `h_net = h_story - t3`.

**Varsayılan nominal tuğla ağırlığı γ=10 kN/m³**, plausible-for-sensitivity search interval 6–20 kN/m³. Adı üzerinde mühendislik varsayımıdır, gerçek malzeme dayanımı/modülü veya TS yük standardı kabulü değildir. Kalınlık adayları 0.09 m ve 0.19 m.

- Kiriş boyunca yük atamalarının nispi aralıkları birleştirilir. Alan hesabında çakışan aralıklar bir kez sayılır; q [kN/m] için aynı kirişteki ayrı yükler integral olarak eklenir.
- `γ_apparent = q_total / (t * h_net)` iki kalınlık için hesaplanır. Seçilen yoğunluk aralığında kalan ve γ=10'a daha yakın aday seçilir. Alternatiflerin ikisi ve şüphe nedeni raporda saklanır.
- `q/q_full = q/(γ_nominal*t*h_net) < 0.75` olduğunda ve γ aralığı buna uygunsa **%50 kapı/pencere açıklığı senaryosu** kabul edilir. Bu, yükten boşluk oranını gerçekten ölçmek değildir: düşük yoğunluk, farklı tuğla, sıva, ayrı yük ataması aynı sayıyı üretebilir.
- B1 `Ak = L_yüklü * t * (1 - açıklık)` [m²] **kesit alanıdır**; C2'deki `L*h_net` [m²] *cephe yüzey alanından* ayrıdır.
- Esnek derzli dolgu seçeneğinde, §4.9.1.3(b) kapsamına girdiği varsayıldığında Ak=0; yalnız seçim yapılması geçerli deneysel bağlantı kapasitesinin kanıtı olmaz.
- Malzeme kayma modülü bağımsız varsayımı Gm=500 MPa; `K_proxy = Gm Ak/h_net` [kN/m] yalnız eleman düzleminde basitleştirilmiş doğrusal kayma *duyarlılık göstergesidir*. B2, TBDY formal rijitlik veya ETABS model güncellemesi değildir; eşdeğer basınç çubuğu hesabı yerine de geçmez.

### Modelde gözlenen koşullu tuğla sınıflandırması

70 kiriş: **36 × 9 cm aday, 34 × 19 cm aday**; **16 kirişte düşük yüke dayalı %50 açıklık varsayımı**, geri kalanlarda tam duvar senaryosu. Özellikle `13.043 kN/m` kayıtları görece ağır/malzeme ve yük bileşimi belirsizliğidir; normal duvarın kesin kalınlığına indirgenemez.

## 3. Kolon, perde ve B1 etkin alanları

Kolonlar: 87 adet, kaynak atamasından tamamı `Column_80x80` (0.64 m²). +0.00: 32 × 0.64 = 20.48 m²; +4.50: 32 × 0.64 = 20.48 m²; +9.00: 23 × 0.64 = 14.72 m². Perdeler: gerçek `Wall Object Connectivity` uç noktaları, `Wall Property Definitions - Specified.Thickness` alanları üzerinden X/Y kesit alanına ayrılır.

| Kat | Yön | Aw [m²] | Ag [m²] | Ak varsayım [m²] | Ae = Aw+Ag+0.15Ak [m²] |
|---|---|---:|---:|---:|---:|
| +0.00 | X | 20.480 | 19.600 | 4.653 | 40.77795 |
| +0.00 | Y | 20.480 | 21.040 | 4.6715 | 42.220725 |
| +4.50 | X | 20.480 | 2.720 | 8.841 | 24.52615 |
| +4.50 | Y | 20.480 | 3.520 | 10.288 | 25.54320 |
| +9.00 | X | 14.720 | 2.720 | 6.650 | 18.43750 |
| +9.00 | Y | 14.720 | 3.520 | 8.460 | 19.50900 |

**ηci,alt/üst (koşullu senaryo):** +0.00/+4.50 X=1.6626, Y≈1.6529; +4.50/+9.00 X≈1.3302, Y≈1.3093. En küçük η≈1.3093; B1 sınırı η<0.80 bu senaryoda tetiklenmiyor. **Formal TBDY 2018 uygunluk `NOT_PROVEN`**, mühendislik release `NOT_READY`.

## 4. Kullanıcıya dönük tek dikey dilim

- `src/tbdy_next/b1_source_bridge.py`: ETABS kaynağı → gerçek şema/birim/SHA → yön/kat → kesit ve açıklık yük varsayımları → mevcut `weak_story_b1.evaluate_b1`.
- `tools/verify_vs06_b1_sources.py`: Windows'ta aynı iki kaynakla bağımsız JSON/HTML B1 hesap dökümü. Orijinal dosyalar değiştirilmez.
- Web `Kat/sistem sonuçları` sekmesi: B1_GEOMETRY ve LC_WDL_OBJECT seçicileri; gevrek/esnek bağlantı; γ ve Gm, %50 açıklık eşiği; hesap butonu; X/Y tablo, kiriş bazlı sınıflandırma ve notlar; JSON/HTML dışa aktarım. Web lokal kaynak dosyalarını yalnız aynı origin endpoint'e gönderir, ETABS COM'a yeniden bağlanmaz.
- Kod asla sayısal ekran sonucundan `MEETS_FORMAL_TBDY` oluşturmaz. Gerçek deprem hesabı gereği model nesli, aktif bodrum kapsamı, fiziksel dolgu ve bağlantı ayrıntısı açık kalır.

**Çalıştır:**

    python -m tools.verify_vs06_b1_sources --geometry <B1_GEOMETRY.json> --wall-loads <LC_WDL_OBJECT.json> --out <B1_RESULT.json> --html <B1_RESULT.html>

**Yönetmelik:** TBDY 2018 Tablo 3.6; §3.6.2.3, esnek bağlantı istisnası §4.9.1.3(b).
