# Check → Source → Schema → Variables → Equation → Result

**Ürün yolu:** EtabsSourceGateway tek COM sahibi, tekrar kullanılabilir tablo okuyucudur. Yeni Check için ayrı kaynak API geliştirmeye gerek yok; yalnız yeni `requested_table_keys` ve tipli `field_binding` tanımlanır. Aktif durum: Windows gerçek `Joint Displacements` şeması henüz okunmadı; ilk işlem bu tablonun şemasını ve verisini almaktır.

| Sıra | Check | Önce gereken tablolar (aday ETABS 23.2 başlıkları) | Gerçek şema durumu | Hesap / kullanım |
|---|---|---|---|---|
| 1 | STORY_DRIFT, Delta_i | Joint Displacements; Story Definitions; Tower and Base Story Definitions; Column Object Connectivity; Joint Coordinates/Point Object Connectivity; Story Drifts | Joint Displacements **henüz gözlenmedi**; Story Drifts ve kat/kolon kaynakları önceki VS04'te gözlendi | Aynı gerçek fiziksel düşey üye, aynı case/step/mod/baz için doğru uç hareketlerini eşleştir; geçerli ise azaltılmış göreli yer değiştirme. RSX/RSY ayrı Max zarf satırlarının üst-alt farkını otomatik Delta_i kabul etme. |
| 2 | EFFECTIVE_DRIFT | Check 1 + gerçek R, I, DD2/DD3 Sae(Tp), story h, kappa ve duvar bağlantısı | Deprem tasarım parametrelerinin kaynağı kısmi | TBDY bağıntılarını uygula; kontrol girdisi kaynağını göster. |
| 3 | BASE_SHEAR | Mass Summary by Story/Group, Response Spectrum Definitions, Modal Periods, Base Reactions, Story Definitions | Kaynaklar önceki VS04/D4'te gözlendi | VtE, gammaE, beta_tE X/Y bağımsız hesap; asgari kesme ile spektral terimi ayrı göster. |
| 4 | GLOBAL_SECOND_ORDER | Story Forces / Joint Displacements / Second-order settings | Gerekli alt küme henüz net değil | Global P-Delta değerlendirmesi, yöntem tekrarı kontrolü. |
| 5 | COLUMN_DESIGN | Frame Force, frame/connectivity, section/material/rebar and combination definitions | Kolon bağlantısı mevcut; tasarım force schema henüz bağlanmadı | Eşzamanlı N-M2-M3; yerel P-delta, PMM/kesme/donatı. |
| 6 | SCWB / JOINT / WALL | Joint topology + approved beam/column capacities + Pier/Area/Section Cuts | Kısmi | TBDY/TS500 check; raporda açık kapsam. |

**Açık ve net fark:** Kaynak toplamak ile kaynak doğrulamasını sonsuz kere tekrarlamak aynı iş değil. Şema bir kere alınır ve proje kapsamında aynı tablonun yapısı değişmedikçe yeniden keşif yapılmaz. Her check ancak kendi ihtiyacı olan en küçük kaynak paketini ister.
