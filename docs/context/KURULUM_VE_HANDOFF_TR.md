# YENI — Güncel yerel bağlam ve devir paketi

17 Kasım 2026 tarihinde gerçek yerel kod ve disk kanıtlarıyla uzlaştırıldı.
Dal: `baseline/local_import`. Uygulama checkpoint'i:
`60938da94b770631c6a5c34a545c8863162ac8a4`.
Tam yayımlanan HEAD, ZIP içindeki `MANIFEST.json` dosyasında yer alır.

Bu paket kalıcı proje yönergeleri ve kanıt indeksidir. Tam proje, ham model/SQLite
yedeği veya mühendislik onayı değildir. Önceki ZIP'in dört temel dosyası güncellendi;
eski D3B kayıtları kendi sürümlerine bağlı olarak korundu.

## Yerelde kurulan düzen

- `AGENTS.md`: yeni oturumda ve bağlam sıkıştırmasından sonra izlenecek okuma sırası,
  tek engine/gateway ilkesi, kullanıcı tercihleri ve kanıt disiplini.
- `docs/CURRENT_STATE.md`: doğrulanmış güncel durum, açık kapılar ve ilk devam adımı.
- `docs/ENGINEERING_GAPS.yaml`: 18 sabit GAP kimliği ve kapsamlı kabul ölçütleri.
  Ek bağımlılık gerektirmeyen JSON sözdizimi kullanır; YAML 1.2 ile uyumludur.
- `docs/VERIFICATION_LEDGER.json`: tarihsel ve yeni yerel kanıtlar; gerçek sürüm,
  komut, ortam, sonuç, sınır, kaynak ve log hash'leri.
- `docs/context/TESTED_FILES_20261117.json`: önceki son testin 401 dosyalık hash kaydı.
- `CONTEXT_VALIDATION.json`: bu kurulumda yapılan bağlam/bütünlük doğrulaması.
- `MANIFEST.json`: ZIP dosyalarının hash'leri ve uzaktan doğrulanmış yayımlama kimliği.

Mevcut sohbet üst klasör `y` üzerinden açıldığı için yerelde `y/AGENTS.md` kısa bir
yönlendirme içerir. Asıl kurallar `y/YENI/AGENTS.md` içindedir. Bu yönlendirmenin
taşınabilir kopyası `docs/context/WORKSPACE_ENTRY_AGENTS.md` dosyasında bulunur;
repo yönergelerinin yerine kopyalanmaz.

## Yeni oturumda başlama

Tercihen Codex projesi olarak doğrudan **YENI repo klasörünü** aç. Sonra şunu yaz:

```text
AGENTS.md ve docs/CURRENT_STATE.md dosyalarını oku. Gerçek repo, branch, HEAD ve
dirty durumu doğrula; aktif işin GAP ve verification kayıtlarıyla uzlaştır.
Yerel yeni işi eski ZIP veya uzak branch ile geri alma. SPECTRAL-MODAL-SOURCE-
QUALIFICATION adımından, mevcut tek gateway/engine/pipeline üzerinden devam et.
Eski testleri yeni çalıştırılmış gibi sunma; açık normatif kapıları kapalı sayma.
```

Yalnız üst klasör açıksa başlangıçta `YENI/AGENTS.md` ve
`YENI/docs/CURRENT_STATE.md` yollarını açıkça belirt. Başka makinede ZIP'i önce
ayrı klasöre aç; mevcut daha yeni bağlamın üzerine körlemesine kopyalama.
Özel `.receipts` kaydı yoksa gerçek replay yapılmış sayılmaz.

## Güncel kapsam ve sınır

87 kolonun yapılandırılmış gerekli kesit alt kümesi 4.422/4.422. Yeni aynı-kaynak
alımı 22 yük deseni, 1.131 üye-vaka çifti ve 100 modal modu içeriyor. Son spektral
replay 3.216 kesitte 38.592 bileşen kıyasını tolerans içinde tamamladı. Bağımsız
Decimal(80) hesabı ve mühürlü rapor/tekrar kanıtları kayıtlı.

Son **önceden çalıştırılmış** regresyon: Windows / Python 3.12.10 / Node 24.22.1;
1.347 Python testi (1 ortam kaynaklı skip), 10 JavaScript test dosyası, 181 temiz
wheel testi. Bu bağlam işleminde kaynak/test hash'leri yeniden kontrol edildi;
regresyon, replay ve canlı ETABS işlemleri yeniden çalıştırılmadı.

R14/R15 hâlâ **0 kapanış / 87 partial**; `ENGINEERING_RELEASE=NOT_READY`.
Sıradaki iş: native modal genlikler, etkin sönüm ve tesadüfi burulma katkılarını
aynı gateway'den bağlamak; ardından mod/yön birleştirmesini bağımsız doğrulamak.
SCWB eksenel talep seçimi, kat kesmesi paylaşımı ve tam alpha iterasyon kabulü açık.

## Belleğin sınırı ve güncellenmesi

Her anlamlı adım sonunda CURRENT_STATE ve ilgili GAP/kanıt kaydını diske güncelle.
GitHub aktarımını bekleme; push yalnız istenen paylaşım noktasında yapılır. Yeni
oturum, dosyaları yeniden okumalıdır. Sohbetin kusursuz otomatik hatırlanması veya
halüsinasyonun tamamen ortadan kalkması garanti edilemez; bu düzen iddiaların
dosya ve kanıtla denetlenmesini sağlar.

Codex'in repo kökünden çalışma dizinine doğru `AGENTS.md` okuma davranışı
[resmî kılavuzda](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
açıklanır. CURRENT_STATE, GAP ve ledger adları bu projenin okuma düzenidir.
Global Codex ayarları değiştirilmedi; ayrı otomasyon veya senkronizasyon servisi kurulmadı.
