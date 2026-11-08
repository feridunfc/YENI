# VS12 / CE-02A — offline kolon kuvvet zinciri

- Mevcut ZIP ve SQLite üzerinde salt okunur türetilmiş görünüm; yeniden içe aktarım gerekmez.
- Gerçek kaynak: 35 birleşim = 6 statik Linear Add + 24 spektral katkılı Linear Add + 5 zarf.
- 2.412 statik adayın 14.472 bileşeni özgün native satırlarla bağımsız karşılaştırıldı.
- Tam Obj/ObjSta/Elm/ElmSta/LoadCase/StepType/StepNum anahtarı ve kaynak satırı korunur.
- N(basınç+) = −P; momentler kN·m → kN·cm ×100. Çekme korunur; J ucunda ek işaret dönüşümü yok.
- 402 tasarım özeti satırı / 1.206 PMM–VMaj–VMin birleşim referansı; 529 tekil statik kaynak bağı.
- 144 çift istasyon satırı; 342 referansta kesin istasyon eşleşmesi yok; bu eksikler örtüşür. 402 PMMRatio hücresi boş.
- Kolonlar paneli: tüm native kuvvetler, statik adaylar, ETABS kritik birleşim izleri; ortak JSON/HTML raporu.
- 577 Python testi; iki Node arayüz regresyonu; 27 yeni test Windows CI kapsamına eklendi.
- Bu paket statik aday ve kritik referans bağlantısıdır. Tam CE-02 tasarım yetkisi, analiz mertebesi ve kapasite kabulü NOT_PROVEN / NOT_READY.

## Kanonik uyarlama ve sınır

TBDY `1440df1b9300f75b1e604204438f5cada9ebd247` talep motorunun isimden
bağımsız sınıflandırması esas alındı; YENI CE-01'in altı bileşenli statik replay'i
korundu. Spektral işaret permütasyonları, yalnız I/J uçlarına indirgeme ve istasyon
yuvarlama bu uyarlamada kullanılmaz. VMaj/VMin ile V2/V3 eşlemesi açık kalır.
ETABS tasarım özetindeki kritik birleşimler, tam seçili tasarım birleşimi listesi değildir.
Momentler CSI yerel eksenlerindedir; kapasite çekirdeğinin eksenlerine eşleme ayrıca doğrulanacak.

Kaynak ZIP SHA-256: `3882b659937626bb3bbfe841e6dbd6c57798fcfcce8e6fa54a683a221210fee3`.
Mevcut CE-01 SQLite SHA-256: `98bef804508076a13d39e12227c5909b93c2e3de19ec2ce297873c1e80dce381`.
Gerçek veri doğrulamasında ikisi de değişmedi. Ham veri Git'e eklenmez.

CSI dayanakları: [FrameForce kimliği ve birimleri](https://docs.csiamerica.com/help-files/etabs-api-2016/html/87689f3e-4175-1627-618b-c4ebae5e89b5.htm),
[frame kuvvet işaretleri ve ofsetler](https://docs.csiamerica.com/help-files/sap/Output/Frame_Element_Internal_Forces_Output_Conventions.htm).

## Windows: ZIP klasörü yerine Git çalışma kopyası

Eski `YENI` klasöründeki `.git` hatası için ayrı `YENI_GIT` klasörünü kullanın:

```powershell
& {
    $branch = "work/vs07-b2-soft-story-20261108"
    $target = Join-Path $env:USERPROFILE "PycharmProjects\YENI_GIT"
    if (!(Test-Path -LiteralPath $target)) {
        git clone --single-branch --branch $branch https://github.com/feridunfc/YENI.git $target
        if ($LASTEXITCODE -ne 0) { throw "Clone başarısız." }
    }
    Set-Location -LiteralPath $target
    git rev-parse --is-inside-work-tree
    if ($LASTEXITCODE -ne 0) { throw "YENI_GIT bir Git deposu değil." }
    if (git status --porcelain) { throw "Yerel değişiklikler var; üzerine yazılmadı." }
    git fetch origin $branch
    if ($LASTEXITCODE -ne 0) { throw "Fetch başarısız." }
    git switch $branch
    if ($LASTEXITCODE -ne 0) { throw "Worker dalına geçilemedi." }
    git pull --ff-only origin $branch
    if ($LASTEXITCODE -ne 0) { throw "Güncelleme tamamlanamadı." }
    if (!(Test-Path .\.venv\Scripts\python.exe)) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Sanal ortam oluşturulamadı." }
    }
    .\.venv\Scripts\python.exe -m pip install -e .
    if ($LASTEXITCODE -ne 0) { throw "Kurulum başarısız." }
    .\.venv\Scripts\python.exe -m unittest discover -s tests -q
    if ($LASTEXITCODE -ne 0) { throw "Test başarısız." }
    git log -1 --oneline
}
```

## Mevcut kaydı açma

CE-01 daha önce içe aktarıldıysa aynı receipt dizinini kullanın; ZIP'i tekrar içe aktarmayın:

```powershell
.\.venv\Scripts\python.exe -m tbdy_next.cli serve --out .receipts --port 8765
```

`http://127.0.0.1:8765` → **Kolonlar** → arşiv → **Görünüm**.
Receipt'ler eski klasördeyse `--out` değerine o klasörün `.receipts` tam yolunu verin.
İlk CE-01 içe aktarımı henüz yapılmadıysa, ZIP yolunu doğrulayıp yalnız bir kez çalıştırın:

```powershell
.\.venv\Scripts\python.exe -m tbdy_next.cli import-column-bank --input "$env:USERPROFILE\Downloads\full-model-evidence(2).zip" --out .receipts
```

CLI özeti: `python -m tbdy_next.cli inspect-column-demands --out .receipts --run-id RUN-…`.
SQLite indirmesi CE-01 kaynak bankasını korur; yeni talep görünümü tam JSON ve HTML çıktısında bulunur.
