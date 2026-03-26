# 🎸 PYPAO: Clean Sound Edition

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![yt-dlp](https://img.shields.io/badge/Powered%20by-yt--dlp-red?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20PC-brightgreen?style=for-the-badge)

**PYPAO** — это продвинутый Telegram-бот для тех, кому важно качество звука. Никакого "мыла" и артефактов при конвертации.

## ✨ Основные фишки

- 🔊 **Original Quality**: Скачивает прямой поток `m4a` (AAC) без перекодирования.
- 📊 **Dynamic Progress**: Живой прогресс-бар с отображением фрагментов (`21/52`).
- 🍪 **Universal Cookies**: 
  - В **Termux** (Android): Авто-обновление из Firefox через `su`.
  - На **ПК**: Умный перебор установленных браузеров (Chrome, Edge, Firefox).
- 🔍 **Inline Power**: Поиск музыки прямо в строке ввода через `@имя_бота`.
- 🖼 **Full Tags**: Автоматическое вшивание обложки и исполнителя.

## 🚀 Установка

### 1. Зависимости
```bash
pip install -U aiogram yt-dlp
Также убедитесь, что в системе установлен ffmpeg.
python pypao.py
При первом запуске бот создаст config.json и попросит токен.
---

### Часть 4: Техническое описание
```text
## ⚙️ Техническая часть

### Логика чистого звука
Бот использует инструкцию `bestaudio[ext=m4a]`, что заставляет YouTube отдавать готовый файл. Это экономит ресурсы процессора и сохраняет звук в первозданном виде.

### Прогресс-бар
Реализован через `asyncio.run_coroutine_threadsafe`, что позволяет обновлять сообщение прямо во время работы `yt-dlp` в отдельном потоке.

Часть 5: Советы по фоновой работе
## 📱 Использование в Termux
Для стабильной работы 24/7 рекомендую использовать `screen`:
```bash
screen -S pypao
python pypao.py
# Свернуть: Ctrl+A, затем D
# Вернуться: screen -r pypao

Enjoy your clean music! 🎧
