from aiogram import Router , F
from aiogram.types import Message , FSInputFile 
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.enums import ChatAction
import os
import uuid
import asyncio
import yt_dlp

router = Router()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@router.message(CommandStart())
async def cmd_start(message : Message):
    await message.bot.send_chat_action(
        chat_id=message.chat.id, 
        action=ChatAction.TYPING
    )
    await asyncio.sleep(1)
    await message.answer(""" Привет! 👋 Добро пожаловать в музыкального бота.

Что я умею:
🎵 /search — найти трек по названию
🎧 /play — включить музыку
📃 /help — список команд

Просто напиши название песни — и я начну! 🚀""")


from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle
from aiogram.types import InputTextMessageContent

router = Router()

@router.inline_query()
async def inline_search(query: InlineQuery):
    text = query.query.strip()

    if not text:
        await query.answer(
            results=[],
            cache_time=1,
            is_personal=True
        )
        return

    # Здесь подключим поиск твоих треков
    await query.answer(
        results=[
            InlineQueryResultArticle(
                id="search_info",
                title=f"Найти: {text}",
                description="Поиск музыки",
                input_message_content=InputTextMessageContent(
                    message_text=f"Ищу музыку: {text}"
                )
            )
        ],
        cache_time=1,
        is_personal=True
    )

@router.message(Command("help"))
async def cmd_help(message : Message):
    await message.bot.send_chat_action(
            chat_id=message.chat.id, 
            action=ChatAction.TYPING
        )
    await asyncio.sleep(0.5)
    await message.answer("67")

@router.message(Command("search"))
async def cmd_search(message: Message):
    # достаём текст после команды
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /search название трека")
        return

    query = parts[1].strip()
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer(f"🔎 Ищу: {query} …")

    # скачиваем через yt-dlp (SoundCloud)
    file_id = uuid.uuid4().hex
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": outtmpl,
    "ffmpeg_location": "/opt/homebrew/bin/",  # ключевая строка
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
    "quiet": True,
    "noplaylist": True,
    "default_search": "scsearch1",
}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)

        # yt-dlp может вернуть playlist-подобную структуру при поиске
        if "entries" in info:
            info = info["entries"][0]

        mp3_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp3")
        if not os.path.exists(mp3_path):
            await status.edit_text("Не удалось получить mp3-файл.")
            return

        title = info.get("title") or query
        performer = info.get("uploader") or "Unknown"

        await message.answer_audio(
            audio=FSInputFile(mp3_path),
            title=title,
            performer=performer,
        )
        await status.delete()
    except Exception as e:
        await status.edit_text(f"Ошибка при поиске/скачивании:\n{e}")
    finally:
        # чистим файл
        for ext in (".mp3", ".webm", ".m4a", ".opus", ".part"):
            p = os.path.join(DOWNLOAD_DIR, f"{file_id}{ext}")
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass