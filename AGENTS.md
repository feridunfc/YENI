# YENI — kalıcı çalışma kuralları

Tek ürün `feridunfc/YENI`; tek runtime `src/tbdy_next`. TBDY, Column,
Column-Engine ve harici raporlar yalnız referanstır. Yeni repo, ikinci solver,
paralel pipeline veya ikinci sonuç sahibi açma. Kullanıcıyla Türkçe iletişim kur.

## Yerel öncelikli çalışma

Kullanıcı Codex'i yerelde çalıştırır; GitHub'a yaklaşık **3–5 sprintte bir**
senkronize eder. Güncel çalışma gerçeği yerel kod + yerel kanıttır; uzak HEAD
sırf GitHub'da olduğu için daha güncel değildir. Hafıza dosyalarını güncellemek
push gerektirmez. GitHub bir paylaşım/yedek/CI noktasıdır, canlı çalışma belleği değil.

Yeni oturumda, bağlam sıkıştırıldıktan sonra veya devralmada:
1. Bu dosyayı ve `docs/CURRENT_STATE.md` dosyasını oku. İlgili GAP ve kanıt
   kayıtlarını `docs/ENGINEERING_GAPS.yaml` ve `docs/VERIFICATION_LEDGER.json`
   içinden seç; her küçük düzenlemede bütün arşivi tekrar yükleme.
2. Repo kökü, yerel dal, HEAD ve dirty durumunu doğrula. `git status --short
   --branch`, `git diff --stat` ve ilgili diff'i incele. Commit edilmemiş ve
   izlenmeyen dosyalar olabilir; HEAD tek başına çalışma ağacını tanımlamaz.
3. Yerel durum dosyası ile kod çelişirse çelişkiyi kaydet ve kod/test kanıtıyla
   uzlaştır. Yeni yerel çalışmayı eski uzak sürüme veya eski ZIP'e geri döndürme.
4. Aktif işi, son doğrulanmış kapsamı ve ilk uygulanabilir adımı kısa belirt;
   mevcut kullanıcı yetkisi kapsamındaki işe devam et. Hafıza kaybı yeni proje
   başlatma veya tamamlanmış kapsamı yeniden yazma gerekçesi değildir.

Bu dosyalar davranış kuralı ve kanıt indeksidir; kendi başlarına mühendislik
onayı veya otomatik çalışan bir hafıza servisi değildir.

## Değişiklik ve senkronizasyon disiplini

Her anlamlı sprint sonunda, görev devrinde ve elle sıkıştırma öncesinde diske
checkpoint yaz: aktif iş, değişen yollar, alınan karar ve gerekçesi, gerçek test
komutları/sonuçları, açık engeller ve sıradaki somut adım. Otomatik sıkıştırmayı
önceden yakalayacağını varsayma; uzun görevde anlamlı ara checkpoint tut.

`CURRENT_STATE.md` kısa operasyon özetidir. GAP kimliklerini koru; kapanışı
kanıta bağla. Ledger'a yeni kimlikle kayıt ekle; eski doğrulamayı sessizce yeni
SHA'ya taşıma. Hatalı kaydı silmek yerine açıklama ve `supersedes` ilişkisi ekle.
Dirty ağaçta test yaptıysan HEAD yanında ilgili dosyaların içerik hash'lerini,
diff kimliğini ve untracked kod kapsamını kaydet; test edileni committed sanma.

Yerel commit yalnız geçerli kullanıcı yetkisiyle, seçilmiş dosyalarla yapılır.
Push her sprintte zorunlu değildir; kullanıcının 3–5 sprintlik aktarım noktasında
veya açık isteğinde yapılır. Önce yerel çalışma ve özel dosyaları koru, sonra
uzak değişikliklerle uzlaştır. `git add .`, reset --hard, clean -fd, force-push,
otomatik rebase/branch değişimi veya kullanıcı işini silme yok. Main merge
ayrı açık yetki ister. Kullanıcının güncel talimatı eski sprint politikalarından
üstündür; mühendislik kabulünün kanıt gereksinimi değişmez.

## Mimari ve hesap sahipliği

Physical / Analysis / Design / Result ayrıdır. Web ve CLI aynı
`engineering/pipeline.py::EnginePipelineRunner` yolunu kullanır.
`design_dependencies.py` bağımlılık/revizyon; `design_scenario.py` senaryo-kaynak
ilişkisi; `pipeline_snapshot.py` ve `receipts.py` değişmez kayıt sahipleridir.
PMM matematiği `column_engine/section_capacity.py`; yerel ikinci mertebe
`column_engine/ts500_column.py`; global P–Δ `engineering/story_pdelta.py`;
α `column_engine/story_alpha.py` ve mevcut `engineering/alpha_iteration.py`;
karma talep `engineering/mixed_demands.py`; spektral aritmetik mevcut
`column_engine/spectral_envelope.py` tarafından yürütülür. Değişiklikten önce
ilgili owner ve testini oku; mevcut hesapları başka dosyada kopyalama.

Yeni finalized sonuçlarda rapor yalnız kayıtlı sonucu sunar; replay ayrı
işlemdir. Eski makbuzlar immutable kalır; legacy uyumluluk yolunu yeni sonuçlara
bulaştırma. Kaynak/model/case-step/physical-cut/kafes/yöntem revizyonları bağlı
olmalı; değişen girdinin downstream sonucunu geçerli bırakma.

## Mühendislik doğruluğu

- Kodlandı, çalıştı, sayısal eşleşti, normatif kabul ve release farklı durumlardır.
  CI PASS veya düşük utilization mühendislik READY vermez. Test, CHECK, düğüm,
  fiziksel eleman ve fixture sayılarını birbirine ekleme; 73/94/242 ayrı kataloglardır.
- Beklenen kapsamı yalnız gelen/başarılı satırlardan üretme. Eksik ve BLOCKED
  örnekler paydada kalır. NOT_APPLICABLE için olumlu yokluk/istisna kanıtı gerekir.
  Kanıtlı FAIL'i genel NOT_PROVEN altında gizleme.
- TEMPLATE, PROPOSED, ALGORITHM_SELECTED_CANDIDATE, mühendis-onaylı seçim ve
  AS_BUILT aynı değildir. Donatı/topoloji/ankraj veya onay uydurma.
- Spektral Max/Min veya sekiz kutu köşesi fiziksel eşzamanlı N–M–V değildir.
  Farklı case, step, eleman tarafı veya model ekstremumlarını tek vektörde birleştirme.
  Aynı yük desenine benzeyen ayrı native case'leri eşitleme; ölçekleri iki kez uygulama.
- Story bir kimliktir, sayısal görünse de kot değildir. Native/yerel boyut
  dönüşümünü bir kez yap. ObjSta/ElmSta, I–J boyu, fiziksel yüz ve TS500 net/etkin
  boy ayrıdır. Model locked durumu analiz nesli kanıtı değildir.
- Global P–Δ / yerel P–δ ve spektrum/α büyütmelerinin sahipliğini ayır. Kaynak
  vektörünü değiştirme veya iterasyonda büyütmeyi biriktirme. Tartışmalı norm
  dalını varsayımla kapatma; dayanak, uygulanabilirlik ve bağımsız oracle kaydet.

## Test ve veri sınırı

İlgili olumlu/olumsuz/sınır testlerini mevcut owner üzerinden çalıştır. Gerekli
regresyon komutu `python tools/test_offline.py`; wheel testi
`python tools/test_installed_wheel.py <wheel_directory>`. Önce doğru yerel
interpreter/import yolunu doğrula. Çalıştırılmayan testi `NOT_RUN` yaz; eski
sayıları yeni turda çalıştırılmış gibi sunma. Bağımsız oracle, primary solver'ın
çıktısını tekrar kullanarak kendini doğrulamamalı.

Canlı ETABS/COM ve yeni analiz, kullanıcı açıkça yetkilendirene kadar ertelenir.
Mevcut offline kaynağı önce ara. Başka fiziksel modellerin verilerini izinsiz
join etme. Public Git'e EDB, ham capture, `.receipts`, özel SQLite, model raporu,
.env veya erişim anahtarı gönderme; hash/özet paylaşımı ham veri erişimi değildir.
Özel kanıtın disk yedeğini ayrıca koru; GitHub kod senkronizasyonu bunun yerine geçmez.
