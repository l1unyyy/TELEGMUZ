import asyncio
import os

import logging



from aiogram import Bot, Dispatcher
from handlers import router

async def main():
    bot = Bot(token = "8253561354:AAFoTdIRMaP7u6ToMXPsHk5eLAqr5R2pTnU")
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