# Check → Source → Schema → Variables → Equation → Result

**Ürün yolu:** EtabsSourceGateway tek COM sahibi, tekrar kullanılabilir tablo okuyucudur. Yeni Check için ayrı kaynak API geliştirilmez; mevcut kaynak ve algoritmalar yeniden kullanılır. VS08 itibarıyla Joint Displacements okunmuş, STORY_DRIFT/C2/B1/B2 kaynak hesapları teslim edilmiştir. Doğrulanmış boş kat istisnasının canlı envanter kabulü bekler; kullanıcı toplu Windows/ETABS kontrolünü geliştirmelerin sonuna bırakmıştır.

| Sıra | Check | Önce gereken tablolar (aday ETABS 23.2 başlıkları) | Gerçek şema durumu | Hesap / kullanım |
|---|---|---|---|---|
| 1 | STORY_DRIFT, Delta_i | Joint Displacements; Story Definitions; Tower and Base Story Definitions; Column Object Connectivity; Point Object Connectivity; Story Drifts | Gerçek şemalar gözlendi; koşullu kaynak hesabı mevcut | RSX/RSY bağımsız Max satırları çıkarılmaz. Eşzamanlı fiziksel uç tasarım ötelemesi ve normatif kabul ayrıca açık. |
| 2 | EFFECTIVE_DRIFT | Check 1 + gerçek R, I, DD2/DD3 Sae(Tp), story h, kappa ve duvar bağlantısı | Deprem tasarım parametrelerinin kaynağı kısmi | TBDY bağıntılarını uygula; kontrol girdisi kaynağını göster. |
| 3 | BASE_SHEAR | Mass Summary by Story/Group, Response Spectrum Definitions, Modal Periods, Base Reactions, Story Definitions | Kaynaklar önceki VS04/D4'te gözlendi | VtE, gammaE, beta_tE X/Y bağımsız hesap; asgari kesme ile spektral terimi ayrı göster. |
| 4 | GLOBAL_SECOND_ORDER | Story Forces / Joint Displacements / Second-order settings | Gerekli alt küme henüz net değil | Global P-Delta değerlendirmesi, yöntem tekrarı kontrolü. |
| 5 | COLUMN_DESIGN | Frame Force, frame/connectivity, section/material/rebar and combination definitions | Kolon bağlantısı mevcut; tasarım force schema henüz bağlanmadı | Eşzamanlı N-M2-M3; yerel P-delta, PMM/kesme/donatı. |
| 6 | SCWB / JOINT / WALL | Joint topology + approved beam/column capacities + Pier/Area/Section Cuts | Kısmi | TBDY/TS500 check; raporda açık kapsam. |

**Kolaydan zora ara dilim:** VS08 `WALL_GEOMETRY_CHECK`, mevcut 30 perde paneli
kaynağını kullanarak üç geometrik alt koşulu UI/JSON/HTML'ye bağlar. Bu teslim,
tablodaki perde dayanım, kuvvet, donatı ve birleşim kontrollerini tamamlamaz.

**VS09 hazır kaynak paketi:** `concrete_fck_80` kullanılan betonda 80 MPa üst
sınırını; `modal_combination_spacing` aynı mod nüfusunun SRSS ayrıklığı ve
gözlenen CQC/SRSS seçimini tamamlar. C25 ve %95/%3 algoritmaları korunur.
Kiriş/döşeme kalınlığı, gerçek serbest açıklık ve tasarım kuvveti gerektiren
kontroller kendi eksik kaynakları alınana kadar sıradaki kaynak bağımlı dilimlerdir.

**VS10 hazır birleşim paketi:** `earthquake_100_30` seçili RS çiftinin tam 100/30
katsayı oranını; `earthquake_direction_pairs` aynı diğer işaretli yükler ve ortak
çarpanda iki baskın yönün kaynak kapsamını hesaplar. D4 grafiği yeniden kullanılır;
24/24 oran ve 8/8 bağlam gözlenmiştir. Zarf, işaret bütünlüğü, tasarım seçimi ve
eşzamanlı kuvvetler ayrı açık koşullardır. Ayrıntı: `VS10_EARTHQUAKE_COMBINATIONS.md`.

**Açık ve net fark:** Kaynak toplamak ile kaynak doğrulamasını sonsuz kere tekrarlamak aynı iş değil. Şema bir kere alınır ve proje kapsamında aynı tablonun yapısı değişmedikçe yeniden keşif yapılmaz. Her check ancak kendi ihtiyacı olan en küçük kaynak paketini ister.
