# R03 — ModelProfile / ComboBook aday sözleşmesi

Kaynak banka 26 \`LoadCases\` ve 35 \`RespCombo\` tanımı barındırır. Native kayıtlar 30 \`Linear Add\` ve 5 \`Envelope\` operatörü gösterir. Bu kaynak bilgileri önemli olsa da tek başına *tasarım birleşimi onayı* değildir.

\`tools/r03_unapproved_combobook.py\` yalnız SHA ile sabit tarihsel bankadan bir DAG üretir. Her graf düğümü, referans türünü (case/combination), özgün referans kimliğini ve katsayıyı tam rasyonel değer olarak saklar. Eksik/cyclic referanslar reddedilir. Özellikle \`LC_DL\`, \`RSX\`, \`Cap_SeisX\` gibi metinlerden G/EX/EY, \(D\), düzey veya yer değiştirme ölçeği yetkisi **türetilmez**.

\`\`\`bash
python tools/r03_unapproved_combobook.py \
  --bank .private_sources/YENI_RUN-5cf449b850fc41eeadcdd7528249f932_columns.zip \
  --output /tmp/r03_unapproved_combobook.json
\`\`\`

\`G,Q,S,H,EX,EY,EZ\` kaynak rolleri ve \`SDS,R,D,I\` aday ModelProfile verileri başlangıçta NULL/NOT_PROVEN'dır. Bu girdiler ayrı onaylı analiz/model kaynağından sağlanmadan \`execution_authority=DENIED\` ve \`engineering_release=NOT_READY\` değişmez.

**Son kabul koşulu:** Kaynak kaynak/tablo şeması, analitik yöntem, fiziksel elemanlar, ilgili TBDY bölümünün uygunluk dalları, gerekli yatay/düşey birleşimler ve analiz nesli ayrı kanıtlanacak. Üretilen graf, yetkili yürütme motoru değil; tasarım bağımlılıklarını kuracak tipli aday sözleşmesidir.

Toplu testler ve canlı ETABS kullanıcı talimatı gereği en sona bırakılmıştır.
