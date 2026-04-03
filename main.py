import os
import asyncio
import threading
import uvicorn
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from handlers import router
import web_app

logging.basicConfig(level=logging.INFO)

def run_webapp():
    """Запускает FastAPI сервер"""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(web_app.app, host="0.0.0.0", port=port)

async def run_bot():
    """Запускает Telegram бота"""
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    print("🦆 Бот Zeta Clicker запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_webapp, daemon=True)
    web_thread.start()
    
    # Запускаем бота (основной поток)
    asyncio.run(run_bot())