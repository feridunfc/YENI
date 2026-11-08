# VS06-C2 — LC_WDL gerçek ETABS 23.2 kaynak kurtarma

## Kaynak olguları (8 Kasım 2026)
- Model: C:\tmp\kompakt_b.EDB, kilitli, birim kodu 6 (kN-m-C).
- ETABS 175 tablo sundu. Beam Object Connectivity: 180 satır, Length birimi m.
- Frame Loads Assignments - Distributed tablo API okuması iki çağrı biçiminde de ETABS_RET_CODE_1 döndürdü.
- Buna rağmen alan metadatası OK: UniqueName, **LoadPattern**, LoadType, RelDistA/B, AbsDistA/B, ForceA/B, vb.
- LoadPattern adlı alan kullanıcıca doğrulanan gerçek LC_WDL desenidir; eski LoadPat varsayımı yanlış.
- Tablo ret=1 değeri fiziksel yükün bulunmadığını kanıtlamaz.

## Aynı genel gateway içinde uygulanan çözüm
Var olan tools/etabs_source_gateway_windows.py, --frame-load-probe verildiğinde aynı kilitli SapModel üzerinden, yakalanmış kirişlerin FrameObj.GetLoadDistributed çıktısını salt-okunur tarar.
Orijinal hata silinmez; frame_load_object_probe ayrı SHA-korumalı kaynak bulgusudur.
Hata veren kirişler boş yük kabul edilmez, unresolved_beams altında tutulur.
Numarik hesaba yalnız eşleşmiş LoadPattern=LC_WDL ve kuvvet tipindeki yük aralıkları girer.
Çakışan nispi aralıklar birleşim olarak alınır; kirişin tüm uzunluğu yüklenmiş varsayılmaz.
Kat bazında aday yüklü uzunluk hesaplanır: L_aday = toplam[L_kiriş × birleşik nispi aralık].
Tahmini duvar yüzeyi = L_aday × varsayılan duvar yüksekliği × kaplama oranı × (1 - açıklık oranı).
Bu B1 dayanım düzensizliği için fiziksel duvarın kesin kanıtı değil, açıkça etiketli aday alan hesabıdır.

## Windows tek dikey çalışma komutları
Mevcut ETABS oturumu açık, kilitli, analizli olmalıdır. Yeni ETABS analizi çalıştırılmaz:

    cd C:\Users\efeya\PycharmProjects\YENI_VS06
    $python = '.\.venv\Scripts\python.exe'
    $stamp = Get-Date -Format yyyyMMdd_HHmmss
    $raw = ".receipts\VS06\LC_WDL_OBJECT_$stamp.json"
    $out = ".receipts\VS06\LC_WDL_AREA_$stamp.json"
    & $python tools\etabs_source_gateway_windows.py capture --table 'Beam Object Connectivity' --table 'Frame Loads Assignments - Distributed' --frame-load-probe --out $raw
    # EXIT 2 = eski tablo RET_CODE_1 korundu; nesne tarama sonucu JSON içine kaydedildi.
    & $python -m tools.review_vs06_wall_capture --input $raw --out $out --pattern LC_WDL --wall-height-m 2.8 --coverage-pct 100 --opening-pct 0 --thickness-m 0.19

## Teslim/kabul sınırı
CI Python 3.11/3.12: 392/392 test PASS. Gerçek Windows FrameObj nesne sorgusu henüz çalıştırılmadı.
PR #5 Draft; VS06 sonunda tek merge, main değişmedi.

CSI resmi API: https://docs.csiamerica.com/help-files/etabs-api-2016/html/327bf456-dfd3-6075-a7aa-3855b3be1dd7.htm
