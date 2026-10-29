import asyncio
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from handlers import router
import logging


async def main():
    load_dotenv()
    bot = Bot(os.getenv("TG_TOKEN"))
    dp = Dispatcher()
    dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def on_startup():
    logging.info("Бот успешно запущен и готов к работе!")
    print("Bot started...")


async def on_shutdown():
    logging.info("Бот останавливает свою работу...")
    print("Bot shutting down....")



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')