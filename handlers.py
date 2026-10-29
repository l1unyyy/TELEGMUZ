from aiogram import Router , F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.enums import ChatAction
import asyncio

router = Router()

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


@router.message(Command("help"))
async def cmd_help(message : Message):
    await message.bot.send_chat_action(
            chat_id=message.chat.id, 
            action=ChatAction.TYPING
        )
    await asyncio.sleep(0.5)
    await message.answer("67")

@router.message(Command("search"))
async def cmd_help(message : Message):
    await message.bot.send_chat_action(
            chat_id=message.chat.id, 
            action=ChatAction.TYPING
        )
    await asyncio.sleep(0.5)
    await message.answer("67")

