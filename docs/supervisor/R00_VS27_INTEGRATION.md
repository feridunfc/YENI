# R00.2 — VS27.3 kaynak entegrasyonu (Codespaces, offline)

**Durum:** Uygulanabilir aracı mevcut; VS27 kaynaklarının otomatik olarak GitHub'a yüklendiği iddia edilmez. Bu işlemi Codespaces'te kaynak paketleriyle yapan operatör, yeni çalışma ağacını gözden geçirip ayrı commit/push yapacaktır.

## Başlangıç

- Esas depo \`feridunfc/YENI\`, yalnız \`recovery/r00-r01-vs27-source-20261112\`.
- Taban VS26 \`14ddf197\`. R00/R01 dosyaları, \`main\`, PR #6 ve eski arşivler korunur.
- VS27 tam paket + VS27.1, VS27.2, VS27.3 SHA'ları \`config/r00_vs27_artifacts.json\` ile doğrulanır.
- Model/ham ZIP/SQLite/EDB repo içinde değildir; \`.private_sources/\` Git tarafından ignore edilir.

## Terminal

\`\`\`bash
git fetch origin
git switch recovery/r00-r01-vs27-source-20261112
git pull --ff-only origin recovery/r00-r01-vs27-source-20261112
git status --short --branch

# Dört VS27 ZIP dosyası .private_sources/ altında olmalı.
# Önce yalnız kaynak fark planı:
python tools/r00_integrate_vs27.py --inputs .private_sources \
  --report /tmp/r00_vs27_import_plan.json

# Plan makulse ve iş ağacı temizse:
python tools/r00_integrate_vs27.py --inputs .private_sources --apply
git status --short
git diff --stat
\`\`\`

**Uyarı:** VS27 zip'in ana kaynakları 371 dosyadır; en büyük örnek JSON/HTML'ler önceki VS26 çalışma ağacında zaten bulunur. Program yalnız yeni/değişmiş izlenen veya yeni eklenen kod ve kaynaklara dokunur. \`.github/workflows/ci.yml\`, \`.gitignore\`, \`docs/supervisor/\`, R00/R01 kontrolleri, manifesto ve ilgili kaynaklar korunur.

**Testler son aşamada:** Henüz \`python -m unittest\` veya canlı ETABS çalıştırılmayacak. İki kaynak arasında çatışma varsa yazılım durur, \`git reset --hard\` önerilmez. Ayrı inceleme ve commit gerekir.

## Sonraki adım

VS27 dosyalarının GitHub recovery branch'e alınmasından sonra R01 tarihsel force bankası ile R02 fiziksel/analiz kimlik sözleşmesi geliştirilecek. Her gerçek modelin run/generation/source SHA'sı korunacak; 12 Kasım arşivi 9 Kasım arşivinden satır taşıyarak tamamlanmış gösterilmeyecek.
