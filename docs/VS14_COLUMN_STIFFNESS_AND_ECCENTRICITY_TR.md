# VS14 / CE-04A — kesit rijitliği ve minimum dışmerkezlik

- Mevcut ZIP'ten 87 kolon ataması, 1 farklı kesit ve 87 malzeme bağı üzerinde A/I22/I33/R22/R33 yeniden hesaplandı; 435 kaynak kıyası eşleşti.
- 80×80 cm kesitte A=6400 cm², I22=I33≈3.413.333,333 cm⁴, r≈230,940108 mm; izinli 0,30h yaklaşımı 240 mm olarak ayrı tutulur. Gözlenen E=34.000 MPa; E×I etkili EI veya analiz rijitliği değildir.
- [TS500/2000 özgün metin kopyası, EMU](https://staff.emu.edu.tr/cemalgenes/Documents/courses/INSA471_2019_20_Bahar/TS500.pdf), §6.3.10 / 6.16: e,min=15+0,03h; burada 39 mm. M2→T3, M3→T2; boy ve referans hesabı Decimal ile korunur.
- 2.412 statik durumda 4.824 eksen referansı: 2.918 üst/eşit, 1.822 alt, 84 basınç değil. Bu dağılım iç istasyonlara yönetmelik PASS/FAIL vermez; hüküm tasarım uç momentine aittir. Kaynak vektörleri değiştirilmez.
- TBDY `1440df1` narinlik/moment büyütme çekirdeği dar olarak uyarlandı. 7.24/7.27 paydası **1−1,3×N/Nk** olarak düzeltildi; pozitif olmayan payda bloklanır. 7.28'de 0,45 sınırı kapsayıcıdır.
- 7.29'un basılı s.27'deki açıklaması serbest boy, sembolü lk diyor. İki okuma ayrı hesaplanır; otomatik yorum seçimi veya çarpım yetkisi verilmez. Serbest boy, k, sway, Rm, uç çiftleri ve analiz esası bağlanmadan gerçek büyütme uygulanmaz.
- Kolonlar görünümü kuvvetler / kesit ön hesapları olarak gruplandı; Kesit rijitliği ve boylar ile Minimum dışmerkezlik referansı eklendi. CLI, tam JSON ve HTML aynı sonucu taşır.
- Bağımsız ham ZIP doğrulaması, farklı dikdörtgen eksen testi, tam eşitlik/yuvarlama karşıörnekleri ve bozuk optional getter izolasyonu tamamlandı; 623 Python testi, iki Node regresyonu; 25 yeni test Windows CI kapsamına eklendi.
- Kaynak ZIP/SQLite, CE-02A ve VS13 sonuç hash'leri değişmedi; yeni veri yazılmadı. CHECK sayısı 16; genel mühendislik kabulü DENIED / NOT_PROVEN / NOT_READY.
- [Mevcut Windows güncelleme ve arşivi açma komutları](VS12_CE02_COLUMN_DEMAND_CHAIN_TR.md#windows-zip-klasörü-yerine-git-çalışma-kopyası) geçerli; yeniden içe aktarım gerekmez. Kullanıcının yerel/toplu testi ve main birleşimi son ortak kabule bırakıldı.
