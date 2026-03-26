# 🎸 PYPAO: Clean Sound Edition

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-orange.svg?style=for-the-badge)](https://docs.aiogram.dev/)
[![yt--dlp](https://img.shields.io/badge/Powered%20by-yt--dlp-red.svg?style=for-the-badge)](https://github.com/yt-dlp/yt-dlp)

**PYPAO** — это мощный Telegram-бот для мгновенного скачивания музыки с YouTube в идеальном качестве без лишних артефактов и перекодировок. Работает как в Termux (Android), так и на ПК (Windows/Linux).

---

## 🔥 Фишки проекта

* **Clean Sound**: Никакого пережатия. Бот вытягивает чистый AAC поток (`.m4a`) напрямую с серверов.
* **Живой Progress Bar**: Отображение процентов и фрагментов загрузки (`21/52`) в реальном времени.
* **Smart Cookies**: 
    * В **Termux** — автоматическое обновление куки из Firefox (нужен Root).
    * На **ПК** — автоматический подхват авторизации из браузеров (Chrome, Firefox, Edge).
* **Inline Mode**: Ищи музыку прямо в поле ввода сообщения через `@твой_бот запрос`.
* **Full Metadata**: Автоматическое вшивание обложек и имен исполнителей (название канала).
* **Shorts & Mobile Ready**: Поддержка всех видов ссылок YouTube.

---

## 🚀 Быстрый старт

### 1. Подготовка (Termux/PC)
Убедись, что у тебя установлен Python и FFmpeg:
```bash
# Для Termux
pkg update && pkg upgrade
pkg install python ffmpeg
