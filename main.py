import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from handlers import router

logging.basicConfig(level=logging.INFO)

async def main():
    init_db()
    
    # Укажи свой прокси (проверь порт!)
    PROXY = "socks5://127.0.0.1:1080"  # Для Psiphon
    # PROXY = "socks5://127.0.0.1:9150"  # Для Tor Browser
    # PROXY = "http://username:password@proxy:port"  # Для HTTP прокси
    
    print(f"🔌 Подключение через прокси: {PROXY}")
    
    # Создаём бота с прокси
    bot = Bot(token=BOT_TOKEN, proxy=PROXY)
    
    # Проверяем подключение
    try:
        me = await bot.get_me()
        print(f"✅ Бот подключился! Юзернейм: @{me.username}")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        print("💀 Прокси не работает или не запущен!")
        print("👉 Запусти Psiphon или Tor Browser и повтори попытку")
        return
    
    dp = Dispatcher()
    dp.include_router(router)
    
    print("🦆 Бот Zeta Clicker запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())