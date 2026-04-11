import os
import json
import sqlite3
import subprocess
import asyncio
import platform
import logging
import yt_dlp
import re
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, FSInputFile
from aiogram.filters import Command

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")

logging.basicConfig(level=logging.INFO)

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    print("\n--- 🛠 ПЕРВИЧНАЯ НАСТРОЙКА ---")
    token = input("Введите токен бота: ").strip()
    config = {"bot_token": token}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    return config

conf = get_config()
bot = Bot(token=conf["bot_token"])
dp = Dispatcher()

def refresh_cookies():
    """Исправленный механизм получения куки в строгом формате Netscape"""
    if not os.path.exists('/data/data/com.termux'):
        return True

    try:
        cmd_profile = "su -c 'ls /data/data/org.mozilla.firefox/files/mozilla/ | grep default'"
        profile = subprocess.check_output(cmd_profile, shell=True).decode().strip().split('\n')[0]
        src_db = f"/data/data/org.mozilla.firefox/files/mozilla/{profile}/cookies.sqlite"
        temp_db = os.path.join(BASE_DIR, "cookies_tmp.sqlite")

        os.system(f"su -c 'cp {src_db} {temp_db} && chmod 666 {temp_db}'")

        if os.path.exists(temp_db):
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            # Netscape формат требует 7 полей, разделенных табуляцией
            query = "SELECT host, 'TRUE', path, CASE WHEN isSecure THEN 'TRUE' ELSE 'FALSE' END, expiry, name, value FROM moz_cookies WHERE host LIKE '%youtube.com%'"
            rows = cursor.execute(query).fetchall()

            with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                f.write("# Netscape HTTP Cookie File\n\n")
                for row in rows:
                    expiry = row[4] if row[4] is not None else 0
                    line = f"{row[0]}\t{row[1]}\t{row[2]}\t{row[3]}\t{expiry}\t{row[5]}\t{row[6]}\n"
                    f.write(line)

            conn.close()
            os.remove(temp_db)
            return True
    except Exception as e:
        logging.error(f"Cookie Error: {e}")
    return False

def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)
    
async def download_logic(url, status_msg):
    """Скачивание с комментированием каждого действия"""
    await status_msg.edit_text("🔄 Скачивание аудио [###]")
    last_upd = 0

    def progress_hook(d):
        nonlocal last_upd
        if d['status'] == 'downloading':
            now = time.time()
            if now - last_upd < 1.5: return
            p = d.get('_percent_str', '0%').replace('%','').strip()
            try:
                pct = float(p)
                bar = "█" * int(pct/10) + "░" * (10 - int(pct/10))
                msg = f"📥 **Загрузка:** `[{bar}] {p}%`"
                asyncio.run_coroutine_threadsafe(status_msg.edit_text(msg, parse_mode="Markdown"), asyncio.get_event_loop())
                last_upd = now
            except: pass

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        'nocheckcertificate': True,
        'progress_hooks': [progress_hook],
        'postprocessors': [
            {'key': 'FFmpegMetadata', 'add_metadata': True},
            {'key': 'EmbedThumbnail'},
        ],
        'quiet': True,
        'noplaylist': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }

    if os.path.exists('/data/data/com.termux'):
        ydl_opts['cookiefile'] = COOKIES_FILE
    else:
        ydl_opts['cookiesfrombrowser'] = ('chrome', 'firefox', 'edge')

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))

            await status_msg.edit_text("🔄 Конвертация [####]")
            temp_path = ydl.prepare_filename(info)
            final_path = os.path.splitext(temp_path)[0] + ".m4a"

            if temp_path != final_path:
                if os.path.exists(final_path): os.remove(final_path)
                os.rename(temp_path, final_path)

            await status_msg.edit_text("🔄 Итоговая реализация [######]")
            return final_path, info.get('title', 'Track'), info.get('uploader', 'YouTube')
    except Exception as e:
        return None, str(e), None
        
@dp.message(F.text.contains("youtu"))
async def handle_link(message: types.Message):

    if not message.via_bot or message.via_bot.id != message.bot.id:
        return

    url_match = re.search(r'(https?://[^\s]+)', message.text)
    if not url_match: return
    url = url_match.group(1)

    status = await message.answer("🔄 Подготовка аудио [ ]")
    await asyncio.to_thread(refresh_cookies)

    ydl_flat_opts = {
        'extract_flat': True,
        'quiet': True,
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None
    }

    try:
        with yt_dlp.YoutubeDL(ydl_flat_opts) as ydl:
            info_dict = await asyncio.to_thread(lambda: ydl.extract_info(url, download=False))

        if 'entries' in info_dict:
            entries = list(info_dict['entries'])
            limit = 20
            await status.edit_text(f"📂 Плейлист: {len(entries)} видео.\n🚀 Качаю первые {min(len(entries), limit)}...")

            for i, entry in enumerate(entries[:limit]):
                v_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry['id']}"
                await status.edit_text(f"🔄 Обработка {i+1}/{min(len(entries), limit)}...")

                f_path, title, author = await download_logic(v_url, status)
                if f_path:
                    audio = FSInputFile(f_path, filename=f"{clean_filename(title)}.m4a")
                    await message.answer_audio(
                        audio,
                        caption=f"✅ {title} | {v_url}",
                        title=title,
                        performer=author
                    )
                    if os.path.exists(f_path): os.remove(f_path)

            await status.edit_text("✅ Плейлист загружен!")

        # ОБРАБОТКА ОДИНОЧНОЙ ССЫЛКИ
        else:
            f_path, title, author = await download_logic(url, status)
            if f_path:
                await status.edit_text(f"📤 Отправка: {title} [#########]")
                audio = FSInputFile(f_path, filename=f"{clean_filename(title)}.m4a")
                await message.answer_audio(
                    audio,
                    caption=f"✅ {title} | {url}",
                    title=title,
                    performer=author
                )
                if os.path.exists(f_path): os.remove(f_path)
                await status.delete()
            else:
                await status.edit_text(f"❌ Ошибка: {title}")

    except Exception as e:
        await status.edit_text(f"❌ Ошибка: {str(e)}")

@dp.inline_query()
async def inline_search(query: InlineQuery):
    text = query.query.strip()
    if len(text) < 2: return
    ydl_opts = {'quiet': True, 'noplaylist': True, 'extract_flat': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(lambda: ydl.extract_info(f"ytsearch10:{text}", download=False))
            results = [InlineQueryResultArticle(
                id=i['id'], title=i['title'][:100],
                description=f"Канал: {i.get('uploader')}",
                input_message_content=InputTextMessageContent(message_text=f"https://www.youtube.com/watch?v={i['id']}")
            ) for i in info['entries']]
            await query.answer(results, cache_time=300)
    except: pass

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🎸 PYPAO v1.01. Created by WALM ")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
