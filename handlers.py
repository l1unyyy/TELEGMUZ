
import os
import json
import uuid
import asyncio
import yt_dlp

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    FSInputFile,
    InlineQuery,
    InlineQueryResultCachedAudio,
)

router = Router()

DOWNLOAD_DIR = "downloads"
CATALOG_FILE = "tracks.json"
STORAGE_CHANNEL_ID = -1004488358151

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

SEARCH_TASKS = set()
background_tasks = set()

# Загружаем сохранённый каталог.
if os.path.exists(CATALOG_FILE):
    try:
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            TRACKS = json.load(f)
    except (json.JSONDecodeError, OSError):
        TRACKS = []
else:
    TRACKS = []


def save_catalog():
    temp_file = CATALOG_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(TRACKS, f, ensure_ascii=False, indent=2)

    os.replace(temp_file, CATALOG_FILE)


def add_track_to_catalog(title, performer, file_id, unique_id, source):
    # Не добавляем один и тот же файл повторно.
    if unique_id and any(
        track.get("file_unique_id") == unique_id
        for track in TRACKS
    ):
        return False

    track = {
        "id": uuid.uuid4().hex,
        "title": title or "Unknown",
        "performer": performer or "Unknown",
        "file_id": file_id,
        "file_unique_id": unique_id,
        "source": source,
    }

    TRACKS.append(track)
    save_catalog()

    print(f"Трек добавлен в базу: {title} — {performer}")
    return True


# Автоматически добавляем музыку, опубликованную в канале.
@router.channel_post(F.chat.id == STORAGE_CHANNEL_ID)
async def save_channel_audio(message: Message):
    try:
        # Обычное аудио Telegram.
        if message.audio:
            audio = message.audio

            title = (
                audio.title
                or message.caption
                or "Без названия"
            )

            performer = audio.performer or "Неизвестный исполнитель"

            added = add_track_to_catalog(
                title=title,
                performer=performer,
                file_id=audio.file_id,
                unique_id=audio.file_unique_id,
                source="telegram_channel",
            )

            if added:
                print(f"Музыка из канала сохранена: {title}")

            return

        # Если песню отправили как документ, преобразуем её в аудио.
        if message.document:
            document = message.document

            mime_type = document.mime_type or ""
            filename = document.file_name or "Без названия"

            if not mime_type.startswith("audio/"):
                return

            title = os.path.splitext(filename)[0]
            performer = "Неизвестный исполнитель"

            # Скачиваем документ во временную папку.
            temp_path = os.path.join(
                DOWNLOAD_DIR,
                f"{uuid.uuid4().hex}_{filename}",
            )

            try:
                await message.bot.download(
                    document,
                    destination=temp_path,
                )

                # Отправляем в канал как аудио,
                # чтобы Telegram выдал audio.file_id.
                stored_message = await message.bot.send_audio(
                    chat_id=STORAGE_CHANNEL_ID,
                    audio=FSInputFile(temp_path),
                    title=title,
                    performer=performer,
                )

                if stored_message.audio:
                    add_track_to_catalog(
                        title=stored_message.audio.title or title,
                        performer=(
                            stored_message.audio.performer
                            or performer
                        ),
                        file_id=stored_message.audio.file_id,
                        unique_id=stored_message.audio.file_unique_id,
                        source="telegram_channel_document",
                    )

            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    except Exception as error:
        print(f"Ошибка сохранения музыки из канала: {error}")


def download_track(url, track_id):
    template = os.path.join(
        DOWNLOAD_DIR,
        f"{track_id}.%(ext)s",
    )

    options = {
        "format": "bestaudio/best",
        "outtmpl": template,
        "ffmpeg_location": "/opt/homebrew/bin/",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)

    if info and info.get("entries"):
        info = next(
            (entry for entry in info["entries"] if entry),
            None,
        )

    mp3_path = os.path.join(DOWNLOAD_DIR, f"{track_id}.mp3")

    if not info or not os.path.exists(mp3_path):
        raise RuntimeError("Не удалось получить MP3.")

    return info, mp3_path


async def search_soundcloud(query):
    def search():
        options = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.extract_info(
                f"scsearch10:{query}",
                download=False,
            )

    data = await asyncio.to_thread(search)

    if not data:
        return []

    return [
        entry
        for entry in (data.get("entries") or [])
        if entry and (entry.get("webpage_url") or entry.get("url"))
    ][:20]


async def prepare_track(bot, entry):
    url = entry.get("webpage_url") or entry.get("url")

    if not url:
        return None

    # Не загружаем один и тот же трек повторно.
    existing = next(
        (track for track in TRACKS if track.get("source") == url),
        None,
    )

    if existing:
        return existing

    track_id = uuid.uuid4().hex
    mp3_path = os.path.join(DOWNLOAD_DIR, f"{track_id}.mp3")

    try:
        info, mp3_path = await asyncio.to_thread(
            download_track,
            url,
            track_id,
        )

        title = info.get("title") or entry.get("title") or "Unknown"
        performer = (
            info.get("uploader")
            or info.get("artist")
            or entry.get("uploader")
            or "Unknown"
        )

        stored_message = await bot.send_audio(
            chat_id=STORAGE_CHANNEL_ID,
            audio=FSInputFile(mp3_path),
            title=title,
            performer=performer,
        )

        if not stored_message.audio:
            return None

        track = {
            "id": uuid.uuid4().hex,
            "title": title,
            "performer": performer,
            "file_id": stored_message.audio.file_id,
            "file_unique_id": stored_message.audio.file_unique_id,
            "source": url,
        }

        TRACKS.append(track)
        save_catalog()

        print(f"Трек сохранён: {title}")
        return track

    except Exception as error:
        print(f"Ошибка обработки трека: {error}")
        return None

    finally:
        for ext in (".mp3", ".webm", ".m4a", ".opus", ".part"):
            path = os.path.join(DOWNLOAD_DIR, f"{track_id}{ext}")
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


async def prepare_search_results(query: str, bot):
    try:
        entries = await search_soundcloud(query)

        if not entries:
            print(f"SoundCloud ничего не нашёл: {query}")
            return

        for entry in entries:
            await prepare_track(bot, entry)

    except Exception as error:
        print(f"Ошибка фонового поиска {query!r}: {error}")


async def run_search_once(bot, query):
    key = query.casefold()

    try:
        await prepare_search_results(query, bot)
    except Exception as error:
        print(f"Ошибка фоновой задачи {query!r}: {error}")
    finally:
        SEARCH_TASKS.discard(key)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! 🎵 Добро пожаловать в музыкального бота.\n\n"
        "🎧 Inline-поиск в любом чате:\n"
        "@musictgvolnabot название песни\n\n"
        "/search название — найти и отправить трек\n"
        "/help — помощь"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🎵 Как пользоваться ботом:\n\n"
        "@musictgvolnabot название песни — inline-поиск\n"
        "/search название песни — поиск и отправка аудио\n"
        "/help — помощь"
    )


# Единственный обработчик inline-запросов.
@router.inline_query()
async def inline_search(inline_query: InlineQuery):
    query = inline_query.query.strip()

    if len(query) < 3:
        await inline_query.answer(
            results=[],
            cache_time=1,
            is_personal=True,
        )
        return

    words = query.casefold().split()

    matches = [
        track
        for track in TRACKS
        if all(
            word in (
                track.get("title", "")
                + " "
                + track.get("performer", "")
            ).casefold()
            for word in words
        )
    ]

    # Уже сохранённые треки показываем сразу.
    if matches:
        await inline_query.answer(
            results=[
                InlineQueryResultCachedAudio(
                    id=track["id"],
                    audio_file_id=track["file_id"],
                    caption=(
                        f'{track["title"]} — {track["performer"]}'
                    ),
                )
                for track in matches[:10]
            ],
            cache_time=1,
            is_personal=True,
        )
        return

    # Сначала быстро отвечаем Telegram, чтобы не было timeout.
    await inline_query.answer(
        results=[],
        cache_time=1,
        is_personal=True,
    )

    # Новые треки ищем и загружаем в фоне.
    key = query.casefold()

    if key not in SEARCH_TASKS:
        SEARCH_TASKS.add(key)
        task = asyncio.create_task(
            run_search_once(inline_query.bot, query)
        )

        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)


@router.message(Command("search"))
async def cmd_search(message: Message):
    parts = (message.text or "").split(maxsplit=1)

    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "Использование: /search название трека"
        )
        return

    query = parts[1].strip()
    status = await message.answer(f"🔎 Ищу: {query}…")

    try:
        entries = await search_soundcloud(query)

        if not entries:
            await status.edit_text(
                "SoundCloud не вернул результатов. "
                "Попробуй другое название."
            )
            return

        track = await prepare_track(message.bot, entries[0])

        if not track:
            await status.edit_text(
                "Не удалось скачать или сохранить трек. "
                "Проверь доступ бота к каналу и FFmpeg."
            )
            return

        await message.answer_audio(
            audio=track["file_id"],
            title=track["title"],
            performer=track["performer"],
        )

        await status.delete()

    except Exception as error:
        print(f"Ошибка команды /search: {error}")
        await status.edit_text(f"Ошибка: {error}")
