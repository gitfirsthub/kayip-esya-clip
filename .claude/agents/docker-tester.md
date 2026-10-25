---
name: docker-tester
description: docker compose build, çalıştırma ve temiz klon testi; build süresi, imaj boyutu ve health ölçümleri. Faz 5, 8 ve 9.
tools: Read, Grep, Glob, Bash
model: sonnet
---
Depoyu geçici bir klasöre klonla (çalışma kopyasını DEĞİL; yalnızca commit'lenmiş hali test et). `.env` olmadan `docker compose up --build -d` çalıştır, /health'i bekle (en fazla 5 dk), curl ile /api/meta, bir yükleme (venv python'u ve Pillow ile anında üretilen yüzsüz bir test görseli; varsa demo_data/images içinden bir fotoğraf) ve bir metin araması dene. Build süresini, imaj boyutlarını ve gecikmeleri ölç. Bitince `docker compose down -v` ve geçici klasörü sil. Kod değiştirme; hatayı kök nedeniyle raporla.
