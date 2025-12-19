# main.py
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

from handlers import router

# 🔐 Загрузка .env
load_dotenv()

# 🛠 Настройки
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = f"/webhook"  # Render будет стучать сюда
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = int(os.getenv("PORT", 8000))  # Render требует PORT

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не найден в .env!")

# 🤖 Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# 📥 Подключаем роутеры
dp.include_router(router)

# 📡 Webhook обработчик
app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)


async def on_startup(bot: Bot):
    """Настройка webhook при старте"""
    webhook_full_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(
        url=webhook_full_url,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True
    )
    logging.info(f"✅ Webhook установлен на: {webhook_full_url}")


async def on_shutdown(bot: Bot):
    """Очистка при выключении"""
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("🧹 Webhook удалён")


async def main():
    logging.basicConfig(level=logging.INFO)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # 🟢 Запуск aiohttp сервера (для Render.com)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)
    await site.start()
    logging.info(f"🚀 Сервер запущен на http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}")

    # 🔁 Держим приложение в работе
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())