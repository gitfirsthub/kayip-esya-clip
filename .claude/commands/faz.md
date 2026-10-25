---
description: docs/PLAN.md'deki bir fazı uygula (ör. /faz 3)
argument-hint: <faz numarası>
---
docs/PLAN.md'deki **Faz $ARGUMENTS**'ı uygula.
1. CLAUDE.md, docs/ILERLEME.md ve docs/PLAN.md'deki Faz $ARGUMENTS bölümünü oku. Önceki fazların kabul kriterleri sağlanmamışsa DUR ve bana söyle.
2. Plan modunda: dosya listesi, adım sırası, commit planı (her biri tek anlamlı değişiklik, Türkçe mesaj), riskler, kabul kriterleri. Onay bekle.
3. Uygula. PLAN'da belirtilen agent varsa ona devret. Kapsam dışına çıkma; yeni fikirleri Fikir Havuzu'na yaz.
4. Her alt adımda testleri çalıştır ve geçince commit at.
5. Faz sonunda: tüm testler → spec-guard agent'ı → kritik ihlal varsa düzelt → docs/ILERLEME.md güncelle (durum, tarih, ölçümler) → docs/AI_KULLANIM_GUNLUGU.md'ye bu fazın kaydı (gerçek istemlerden örnekler ve yanılgılar dahil) → son commit.
6. Bana şunları raporla: ne yapıldı, ne doğrulanmadı, benim elle test etmem gerekenler, push komutu (onayımla çalıştırılacak).
