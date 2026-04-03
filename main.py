import os
import asyncio
import threading
import uvicorn
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import BOT_TOKEN
from database import init_db
from handlers import router
from web_app import app as web_app

logging.basicConfig(level=logging.INFO)

def run_webapp():
    """Запускает FastAPI сервер в отдельном потоке"""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(web_app, host="0.0.0.0", port=port, log_level="info")

async def run_bot():
    """Запускает Telegram бота"""
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    # Команда /game для Mini App
    @dp.message(Command("game"))
    async def cmd_game(message):
        user_id = message.from_user.id
        base_url = os.environ.get("PUBLIC_URL", "https://zeta-clicker-bot-2.up.railway.app")
        web_app_url = f"{base_url}/?user_id={user_id}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🎮 Играть в Zeta Clicker! 🦆",
                web_app=WebAppInfo(url=web_app_url)
            )]
        ])
        
        await message.answer(
            "🦆 **Zeta Clicker — Mini App версия!**\n\n"
            "Нажми на кнопку ниже, чтобы открыть игру с живыми анимациями!\n\n"
            "✨ **Фичи:**\n"
            "• Живая анимация клика\n"
            "• Система энергии\n"
            "• Уровни и прокачка\n"
            "• Всплывающие числа\n\n"
            "Погнали! 🚀",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    print("🦆 Бот Zeta Clicker запущен!")
    await dp.start_polling(bot)

async def main():
    web_thread = threading.Thread(target=run_webapp, daemon=True)
    web_thread.start()
    print(f"🌐 Веб-сервер запущен на порту {os.environ.get('PORT', 8000)}")
    await run_bot()

if __name__ == "__main__":
    asyncio.run(main())