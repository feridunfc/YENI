# R02 — Fiziksel / analiz nesnesi kimlik defteri

**Amaç:** Tarihsel, SHA ile sabit \`RUN-5cf449b...\` kaynağındaki 87 seçilmiş fiziksel kolonu bunlara ait analiz elemanları, I/J uç noktaları, fiziksel kesit adı ve tüm gözlenen istasyonlarına eşlemek.

R02, yeni bir ETABS capture yapmaz. \`--bank\` dosyası 9 Kasım'daki native veri bankasıdır; 12 Kasım'ın boş \`FrameForce\` arşiviyle **birleştirilmez**. Bu 87 kolonun bütün bina kolonları olduğu iddia edilmez.

\`\`\`bash
python tools/r02_physical_analysis_ledger.py \
  --bank .private_sources/YENI_RUN-5cf449b850fc41eeadcdd7528249f932_columns.zip \
  --output /tmp/r02_physical_analysis_ledger.json
\`\`\`

Defter her kolon için fiziksel Obj, I/J point ID, XYZ, doğrulanabilir nesne boyu, parçalara ayrılmış \`Elm\` analiz elemanları, \`ObjSta/ElmSta\` sayıları ve kaynak hatalarını kaydeder. Bir kesite/senaryoya veya aynı koordinattaki farklı elemanlara ait kuvvetler yanlışlıkla birleştirilmez.

**HOLD:** Kullanılmış ETABS uç kesiti, fiziksel birleşim yüzü, etkin TS500 boyu, global model nesli, gerçek yerleştirilmiş donatı ve bütün bina kapsamı henüz nitelikli değildir. Hesap sonucu \`engineering_release=NOT_READY\`. R03 ve R07'nin veri girişi olarak bu kimlik defteri kullanılabilir; normatif uygunluk için doğrudan kullanılamaz.

**Test politikası:** Toplu offline unittest, golden ve Windows/ETABS kabulü son aşamada. Kaynağın sürüm kimliğinin korunması tek başına mühendislik onayı değildir.
