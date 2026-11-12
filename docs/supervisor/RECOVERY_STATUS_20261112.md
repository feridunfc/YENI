# Recovery — Aktif çalışma defteri (12.11.2026)

**GitHub:** \`feridunfc/YENI\` / \`recovery/r00-r01-vs27-source-20261112\`. PR #7 taslak, VS26 tabanına göre açıldı; VS26 PR #6 ve \`main\` korunur.

| İş | Yazılım teslimi | Kaynak/kanıt yetkisi | Kabul |
|---|---|---|---|
| R00 | SHA sabit ZIP stage ve safe import aracı | VS27.1→2→3 zinciri | Kaynak entegresi Codespaces çalışmasına bağlı; tam test ertelendi |
| R01 | Tarihsel native ZIP bankası + offline 6-combo replayer | 87 kolon, 34.170 satır; 2.412 statik satır, 14.472 bileşen referans | Kod yazıldı; gün sonu test/independent acceptance bekliyor |
| R02 | Obj/I-J/Elm/ObjSta/ElmSta bağlama defteri | Fiziksel ve analitik ayrı kimlik, gerçek birleşim yüzü kanıt değil | Kod yazıldı; test ve kaynak değerlendirmesi bekliyor |
| R03 | 26 case/35 combo aday DAG, katsayıları koruyarak | G/Q/S/H/EX/EY/EZ ve SDS/R/D/I otomatik atanmıyor | Kod yazıldı; normatif yetki DENIED |
| R04+ | Bağımsız tasarım/golden zinciri | Genel analiz nesli ve gerçek kaynak gerekir | Başlanmadı |

Kaynak koşulları:
- 9 Kasım banka ZIP SHA \`4a5bc739980178b519b8554f9e323fc222e6510c819a26569c9fbf296a763573\`.
- Native kaynak ZIP SHA \`3882b659937626bb3bbfe841e6dbd6c57798fcfcce8e6fa54a683a221210fee3\`.
- 12 Kasım yeni 87 kolon ZIP SHA \`0ff4186c60b49adee1c7fab2f1f63c528f74491ed946b163fc5c161eb4f28111\`; kuvvet kaydı 0, eski run ile karıştırılmaz.

**Test politikası:** Kullanıcının talebiyle toplu unit/golden/Windows testler ve canlı ETABS gün sonuna bırakıldı. GitHub otomatik CI çalışırsa bu tek başına Supervisor engineering acceptance değildir.

**Sonraki teslim:** VS27 stage paketlerini Codespaces'te güvenle uygula, raporlanmış dosya diff'ini incele, ardından R01→R03 defterlerini aynı kaynak arşivine karşı sırayla üret. Denetim sonrası kaynak kod ayrı commit/push ile PR #7'ye girer; merge HOLD.
