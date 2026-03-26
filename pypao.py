import os
import json
import sqlite3
import subprocess
import asyncio
import platform
import logging
import yt_dlp
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, FSInputFile
from aiogram.filters import Command

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")

final_youtube_url = None

logging.basicConfig(level=logging.INFO)

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    token = input("Введите токен бота: ").strip()
    config = {"bot_token": token}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    return config

conf = get_config()
bot = Bot(token=conf["bot_token"])
dp = Dispatcher()

def refresh_cookies():
    system = platform.system()
    is_termux = os.path.exists('/data/data/com.termux')

    if is_termux:
        try:
            cmd_profile = "su -c 'ls /data/data/org.mozilla.firefox/files/mozilla/ | grep default'"
            profile = subprocess.check_output(cmd_profile, shell=True).decode().strip().split('\n')[0]
            src_db = f"/data/data/org.mozilla.firefox/files/mozilla/{profile}/cookies.sqlite"
            temp_db = os.path.join(BASE_DIR, "cookies_tmp.sqlite")
            os.system(f"su -c 'cp {src_db} {temp_db} && chmod 666 {temp_db}'")

            if os.path.exists(temp_db):
                conn = sqlite3.connect(temp_db)
                query = "SELECT host, 'TRUE', path, 'FALSE', expiry, name, value FROM moz_cookies WHERE host LIKE '%youtube.com%'"
                rows = conn.cursor().execute(query).fetchall()
                with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                    f.write("# Netscape HTTP Cookie File\n\n")
                    for row in rows:
                        f.write("\t".join(map(str, row)) + "\n")
                conn.close()
                os.remove(temp_db)
                return True
        except Exception as e:
            logging.error(f"Ошибка куки в Termux: {e}")
    else:
        logging.info(f"Запуск на ПК ({system}), куки будут взяты из браузера.")
        return True
    return False

def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

@dp.inline_query()
async def inline_search(query: InlineQuery):
    global final_youtube_url
    text = query.query.strip()
    if not text or len(text) < 2: return
    await asyncio.to_thread(refresh_cookies)
    ydl_opts = {'quiet': True, 'noplaylist': True, 'extract_flat': True, 'cookiefile': COOKIES_FILE, 'nocheckcertificate': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(lambda: ydl.extract_info(f"ytsearch10:{text}", download=False))
            entries = info.get('entries', [])
        results = []
        for item in entries:
            v_id = item.get('id')
            if not v_id: continue
            results.append(InlineQueryResultArticle(
                id=v_id, title=item.get('title', 'Video')[:100],
                description=f"Канал: {item.get('uploader', 'YouTube')}",
                input_message_content=InputTextMessageContent(message_text=f"https://www.youtube.com/watch?v={v_id}")
            ))
        await query.answer(results, cache_time=300)
    except: pass

@dp.message(F.text.contains("youtu"))
async def handle_link(message: types.Message):
    v_id_match = re.search(r'(?:v=|\/be\/|\/shorts\/)([a-zA-Z0-9_-]{11})', message.text)
    if not v_id_match: return
    v_id = v_id_match.group(1)

    status = await message.answer("🔄 Подготовка аудио [ ]")
    await asyncio.to_thread(refresh_cookies)

    file_path, title, author = await download_logic(v_id, status)

    if file_path and os.path.exists(file_path):
        await status.edit_text(f"📤 Отправка: {title} [#########]")
        audio = FSInputFile(file_path, filename=f"{clean_filename(title)}.m4a")
        try:
            await message.answer_audio(
                audio,
                caption=f"✅ {title} | {final_youtube_url}",
                title=title,
                performer=author
            )
            os.remove(file_path)
            await status.delete()
        except Exception as e:
            await status.edit_text(f"❌ Ошибка отправки: {e}")
    else:
        await status.edit_text(f"❌ Ошибка: {title}")

async def download_logic(v_id, status):
    global final_youtube_url
    url = f"https://www.youtube.com/watch?v={v_id}"
    final_youtube_url = url
    last_upd = 0

    def progress_hook(d):
        nonlocal last_upd
        if d['status'] == 'downloading':
            import time
            now = time.time()
            if now - last_upd < 1.5: return

            p = d.get('_percent_str', '0%').replace('%','').strip()
            f_idx = d.get('fragment_index', '1')
            f_cnt = d.get('fragment_count', '?')

            try:
                pct = float(p)
                bar = "█" * int(pct/10) + "░" * (10 - int(pct/10))
                msg = f"📥 **Загрузка:** `[{bar}] {p}%`\n🧩 Часть: `{f_idx}/{f_cnt}`"
                asyncio.run_coroutine_threadsafe(status.edit_text(msg, parse_mode="Markdown"), asyncio.get_event_loop())
                last_upd = now
            except: pass

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, f"{v_id}.%(ext)s"),
        'nocheckcertificate': True,
        'progress_hooks': [progress_hook],
        'postprocessors': [
            {'key': 'FFmpegMetadata', 'add_metadata': True},
            {'key': 'EmbedThumbnail'},
        ],
        'quiet': True,
        'ignoreerrors': True,
    }

    if os.path.exists('/data/data/com.termux'):
        ydl_opts['cookiefile'] = COOKIES_FILE
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await status.edit_text("📥 Инициализация потока (Termux)...")
                info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
                return await process_finish(info, status)
        except Exception as e:
            return None, f"Ошибка Termux: {str(e)}", None
    else:
        for browser in ['chrome', 'firefox', 'edge', 'opera']:
            try:
                c_opts = ydl_opts.copy()
                c_opts['cookiesfrombrowser'] = (browser,)
                with yt_dlp.YoutubeDL(c_opts) as ydl:
                    await status.edit_text(f"🔄 Проверка браузера: {browser}...")
                    info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
                    if info: return await process_finish(info, status)
            except: continue

    return None, "Не удалось найти подходящие куки", None

async def process_finish(info, status):
    temp_path = os.path.join(DOWNLOAD_DIR, f"{info['id']}.{info['ext']}")

    final_path = os.path.splitext(temp_path)[0] + ".m4a"

    if temp_path != final_path:
        await status.edit_text("📦 Финализация формата...")
        if os.path.exists(final_path): os.remove(final_path)
        os.rename(temp_path, final_path)

    return final_path, info.get('title', 'Track'), info.get('uploader', 'YouTube')

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🎸 **ПИПЯО: STABLE**\n\n• Любые ссылки (Shorts, Mobile, Web)\n• Авторы каналов в тегах")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
